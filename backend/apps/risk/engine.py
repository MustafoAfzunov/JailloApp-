"""Risk engine: turns sensor data, satellite hotspots and weather into 0-100 risk scores.

Scores are indicative heuristics, not official forecasts. Avalanche in particular is a
weather-based index and never replaces official avalanche bulletins.
"""
import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone

from apps.common.constants import (
    HAZARD_AVALANCHE,
    HAZARD_FIRE,
    HAZARD_FLOOD,
    HAZARD_MUDFLOW,
    level_from_score,
)
from apps.common.geo import bbox, haversine_km
from apps.sensors.models import Node, Reading, VibrationEvent

from .models import FireHotspot, RiskAssessment, RiskHistory
from .weather import latest_weather

log = logging.getLogger(__name__)


@dataclass
class HazardResult:
    hazard: str
    score: float = 0.0
    reasons: list = field(default_factory=list)
    inputs: dict = field(default_factory=dict)
    eta_seconds: int | None = None

    @property
    def level(self):
        return level_from_score(self.score)

    @property
    def details(self):
        return {"reasons": self.reasons, "inputs": self.inputs}


# ---------------------------------------------------------------- helpers
def _water_trend(node, now):
    """Return (rise_cm_per_hour or None, latest_level_cm or None) over the last hour."""
    pts = list(
        Reading.objects.filter(
            node=node, water_level_cm__isnull=False, created_at__gte=now - timedelta(hours=1)
        )
        .order_by("created_at")
        .values_list("created_at", "water_level_cm")
    )
    if not pts:
        return None, None
    latest = pts[-1][1]
    if len(pts) < 2:
        return None, latest
    hours = (pts[-1][0] - pts[0][0]).total_seconds() / 3600
    if hours < 5 / 60:  # under 5 minutes of data is too short for a rate
        return None, latest
    return (latest - pts[0][1]) / hours, latest


def estimate_mudflow_eta(village, first_events, now):
    """Estimate seconds until a mudflow reaches the village.

    first_events: {node_id: earliest recent mudflow VibrationEvent (node preloaded)}.
    Speed comes from the time between consecutive upstream/downstream nodes; with a single
    node an assumed speed is used and flagged.
    """
    triggered = sorted(first_events.values(), key=lambda e: (e.node.flow_order, e.created_at))
    last = triggered[-1]
    dist_left = haversine_km(last.node.lat, last.node.lon, village.lat, village.lon) * settings.PATH_FACTOR

    speed = None
    for a, b in zip(triggered, triggered[1:]):
        hours = (b.created_at - a.created_at).total_seconds() / 3600
        if hours <= 0:
            continue
        d = haversine_km(a.node.lat, a.node.lon, b.node.lat, b.node.lon) * settings.PATH_FACTOR
        v = d / hours
        if 3 <= v <= 120:
            speed = v
    assumed = speed is None
    if assumed:
        speed = settings.MUDFLOW_ASSUMED_SPEED_KMH

    elapsed_h = (now - last.created_at).total_seconds() / 3600
    eta_h = max(0.0, dist_left / speed - elapsed_h)
    info = {
        "nodes_triggered": len(triggered),
        "speed_kmh": round(speed, 1),
        "speed_assumed": assumed,
        "distance_left_km": round(dist_left, 2),
    }
    return int(eta_h * 3600), info


# ---------------------------------------------------------------- hazards
def assess_mudflow(village, nodes, wx, now):
    r = HazardResult(HAZARD_MUDFLOW)
    events = list(
        VibrationEvent.objects.filter(
            node__in=nodes, classification="mudflow", created_at__gte=now - timedelta(minutes=20)
        )
        .select_related("node")
        .order_by("created_at")
    )
    first = {}
    for e in events:
        first.setdefault(e.node_id, e)
    max_conf = max((e.confidence for e in events), default=0.0)

    vib = 0.0
    if len(first) >= 2:
        vib = min(100.0, 82 + 10 * max_conf)
        r.reasons.append(f"Mudflow vibration confirmed by {len(first)} nodes")
    elif len(first) == 1:
        vib = 50 + 15 * max_conf
        r.reasons.append("Mudflow vibration at 1 node (awaiting confirmation from a second node)")

    gauge = (
        Reading.objects.filter(node__in=nodes, created_at__gte=now - timedelta(hours=24)).aggregate(
            s=Sum("rain_mm")
        )["s"]
        or 0.0
    )
    prev24 = wx.get("precip_prev24_mm", 0.0) if wx else 0.0
    next24 = wx.get("precip_next24_mm", 0.0) if wx else 0.0
    rain24 = max(gauge, prev24)
    rain_score = min(30.0, 30.0 * (rain24 + 0.5 * next24) / 60.0)

    rises = [t for t in (_water_trend(n, now)[0] for n in nodes) if t is not None]
    rise = max(rises, default=None)
    water_score = min(20.0, max(0.0, rise) / 30.0 * 20.0) if rise is not None else 0.0

    env = rain_score + water_score
    r.score = min(100.0, vib + 0.5 * env) if vib else env * 0.6
    if rain24 >= 10:
        r.reasons.append(f"Rain {rain24:.0f} mm in the last 24 h")
    if next24 >= 10:
        r.reasons.append(f"Forecast {next24:.0f} mm in the next 24 h")
    if rise is not None and rise > 5:
        r.reasons.append(f"Water rising {rise:.0f} cm/h")

    r.inputs = {
        "triggered_nodes": [e.node.device_id for e in first.values()],
        "max_confidence": round(max_conf, 2),
        "rain_24h_mm": round(rain24, 1),
        "water_rise_cm_per_h": None if rise is None else round(rise, 1),
    }
    if first:
        r.eta_seconds, eta_info = estimate_mudflow_eta(village, first, now)
        r.inputs["eta"] = eta_info
    return r


def assess_flood(village, nodes, wx, now):
    r = HazardResult(HAZARD_FLOOD)
    level_score, rise_best, per_node = 0.0, None, {}
    for n in nodes:
        rise, latest = _water_trend(n, now)
        if latest is None:
            continue
        per_node[n.device_id] = {"level_cm": latest, "rise_cm_per_h": None if rise is None else round(rise, 1)}
        if n.water_alert_cm:
            level_score = max(level_score, min(60.0, 60.0 * latest / n.water_alert_cm))
            if latest >= n.water_alert_cm:
                r.reasons.append(f"Water at {n.device_id} reached the flood level ({latest:.0f} cm)")
        if rise is not None:
            rise_best = rise if rise_best is None else max(rise_best, rise)

    rise_score = min(25.0, max(0.0, rise_best)) if rise_best is not None else 0.0
    prev24 = wx.get("precip_prev24_mm", 0.0) if wx else 0.0
    next24 = wx.get("precip_next24_mm", 0.0) if wx else 0.0
    rain_score = min(25.0, 25.0 * (prev24 + 0.5 * next24) / 80.0)

    r.score = min(100.0, level_score + rise_score + rain_score)
    if rise_best is not None and rise_best > 5:
        r.reasons.append(f"Water rising {rise_best:.0f} cm/h")
    if prev24 + next24 >= 30:
        r.reasons.append(f"Rain: {prev24:.0f} mm past 24 h, {next24:.0f} mm forecast")
    r.inputs = {"nodes": per_node, "precip_prev24_mm": prev24, "precip_next24_mm": next24}
    return r


def assess_avalanche(village, wx, now):
    r = HazardResult(HAZARD_AVALANCHE)
    if not wx:
        r.reasons.append("Weather data unavailable")
        r.inputs = {"weather": "unavailable"}
        return r
    snow24, next24 = wx["snowfall_prev24_cm"], wx["snowfall_next24_cm"]
    depth, tmax, wind = wx["snow_depth_m"], wx["temp_max_prev24_c"], wx["wind_max_24h_kmh"]

    score = min(40.0, snow24) + min(15.0, next24 * 0.5)
    if snow24 >= 10:
        r.reasons.append(f"{snow24:.0f} cm of new snow in 24 h")
    if next24 >= 10:
        r.reasons.append(f"{next24:.0f} cm of snow forecast")
    if depth >= 0.5:
        score += 10
        r.reasons.append(f"Deep snowpack ({depth:.1f} m)")
    if depth >= 0.2 and tmax >= -1:
        score += 20
        r.reasons.append(f"Warming above freezing ({tmax:.0f} °C) on a snowpack")
    if wind >= 40 and (snow24 >= 5 or depth >= 0.3):
        score += min(15.0, (wind - 30) / 2)
        r.reasons.append(f"Strong wind ({wind:.0f} km/h) loading slopes")
    r.score = min(100.0, score)
    r.inputs = {k: wx[k] for k in ("snowfall_prev24_cm", "snowfall_next24_cm", "snow_depth_m", "temp_max_prev24_c", "wind_max_24h_kmh")}
    return r


def assess_fire(village, nodes, wx, now):
    r = HazardResult(HAZARD_FIRE)
    since = now - timedelta(minutes=10)

    triggered = []
    crackle = False
    for n in nodes:
        rd = (
            Reading.objects.filter(node=n, created_at__gte=since)
            .filter(Q(smoke_ppm__gte=settings.SMOKE_ALERT_PPM) | Q(temperature_c__gte=settings.FIRE_TEMP_ALERT_C))
            .order_by("-created_at")
            .first()
        )
        if rd:
            triggered.append(n.device_id)
            crackle = crackle or (rd.extra.get("crackle_score", 0) >= 0.6)
    sensor = 0.0
    if triggered:
        sensor = 55.0
        r.reasons.append(f"Smoke or high temperature at {', '.join(triggered)}")
        if crackle:
            sensor += 10
            r.reasons.append("Fire crackle sound detected")
        if len(triggered) >= 2:
            sensor += 10
            r.reasons.append("Confirmed by more than one sensor")

    sat, nearest = 0.0, None
    lat_min, lat_max, lon_min, lon_max = bbox(village.lat, village.lon, 30)
    hotspots = FireHotspot.objects.filter(
        acquired_at__gte=now - timedelta(hours=24),
        latitude__range=(lat_min, lat_max),
        longitude__range=(lon_min, lon_max),
    ).exclude(confidence="low")
    for h in hotspots:
        d_v = haversine_km(village.lat, village.lon, h.latitude, h.longitude)
        d_n = min((haversine_km(n.lat, n.lon, h.latitude, h.longitude) for n in nodes), default=999.0)
        if d_n <= 5 or d_v <= 8:
            s = 35.0
        elif d_n <= 10 or d_v <= 15:
            s = 25.0
        elif d_v <= 25:
            s = 10.0
        else:
            continue
        if s > sat:
            sat, nearest = s, min(d_v, d_n)
    if sat:
        r.reasons.append(f"Satellite fire hotspot about {nearest:.0f} km away")

    dry = 0.0
    if wx and wx["precip_prev24_mm"] < 0.5 and wx["temp_max_prev24_c"] >= 30:
        dry = 5.0
        r.reasons.append("Hot and dry weather")

    r.score = min(100.0, sensor + sat + dry)
    r.inputs = {
        "sensor_nodes": triggered,
        "nearest_hotspot_km": None if nearest is None else round(nearest, 1),
    }
    return r


# ---------------------------------------------------------------- orchestration
def _save(village, results, now):
    for r in results:
        cur = RiskAssessment.objects.filter(village=village, hazard=r.hazard).first()
        if cur is None:
            RiskAssessment.objects.create(
                village=village, hazard=r.hazard, level=r.level, score=round(r.score, 1),
                details=r.details, eta_seconds=r.eta_seconds, level_since=now,
            )
            RiskHistory.objects.create(village=village, hazard=r.hazard, level=r.level, score=round(r.score, 1), created_at=now)
            continue
        changed = cur.level != r.level
        cur.level, cur.score, cur.details, cur.eta_seconds = r.level, round(r.score, 1), r.details, r.eta_seconds
        if changed:
            cur.level_since = now
            RiskHistory.objects.create(village=village, hazard=r.hazard, level=r.level, score=round(r.score, 1), created_at=now)
        cur.save()


def evaluate_village(village, now=None, notify=True):
    """Recompute all hazards for a village, store them and (optionally) sync alerts."""
    now = now or timezone.now()
    nodes = list(Node.objects.filter(village=village, is_active=True))
    wx = latest_weather(village)
    results = [
        assess_mudflow(village, nodes, wx, now),
        assess_flood(village, nodes, wx, now),
        assess_avalanche(village, wx, now),
        assess_fire(village, nodes, wx, now),
    ]
    _save(village, results, now)
    if notify:
        from apps.alerts.services import sync_from_results

        sync_from_results(village, results, now)
    return results


def evaluate_all(notify=True):
    from apps.geo.models import Village

    return {v.slug: evaluate_village(v, notify=notify) for v in Village.objects.all()}
