"""Builds the data for the Home and Safety-map screens from the rest of the system."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.alerts.models import Alert
from apps.alerts.serializers import AlertSerializer
from apps.common.constants import HAZARDS, LEVEL_HIGH, LEVEL_LOW, LEVEL_MEDIUM, LEVEL_RANK, max_level
from apps.common.geo import haversine_km
from apps.geo.models import Village, VillageContact
from apps.market.models import Listing
from apps.risk.models import RiskAssessment
from apps.sensors.models import Reading

from . import texts

WALK_KMH = 4.5
PATH_FACTOR = 1.3  # streets and slopes are longer than the straight line
WEATHER_MAX_AGE = timedelta(hours=24)


def pick_village(slug, user):
    if slug:
        village = Village.objects.filter(slug=slug).first()
        if village:
            return village
    if user is not None and user.is_authenticated and user.village_id:
        return user.village
    return Village.objects.filter(slug="ak-tash").first() or Village.objects.first()


def overall(village):
    levels = {a.hazard: a.level for a in RiskAssessment.objects.filter(village=village)}
    return max_level(levels.values()), {h: levels.get(h, LEVEL_LOW) for h in HAZARDS}


def origin_for(village, user):
    """Where the user is for distance maths: their home, else the village centre."""
    if user is not None and user.is_authenticated and user.home_lat is not None and user.home_lon is not None:
        return user.home_lat, user.home_lon, True
    return village.lat, village.lon, False


def shelter_card(point, origin, lang):
    km = haversine_km(origin[0], origin[1], point.lat, point.lon) * PATH_FACTOR
    return {
        "id": point.id,
        "name": point.name_for(lang),
        "notes": point.notes_for(lang),
        "lat": point.lat,
        "lon": point.lon,
        "is_primary": point.is_primary,
        "has_clinic": point.has_clinic,
        "has_water": point.has_water,
        "distance_m": int(round(km * 1000 / 10.0) * 10),
        "walk_minutes": max(1, int(round(km / WALK_KMH * 60))),
    }


def shelters(village, origin, lang):
    cards = [shelter_card(p, origin, lang) for p in village.evacuation_points.all()]
    cards.sort(key=lambda c: (not c["is_primary"], c["distance_m"]))
    return cards


def weather_card(village, lang):
    snap = village.weather.first()
    if not snap or snap.fetched_at < timezone.now() - WEATHER_MAX_AGE:
        return None
    s = snap.summary
    condition = s.get("condition")
    return {
        "temp_c": round(s.get("temp_now_c", 0)),
        "condition": condition,
        "label": texts.CONDITIONS[lang].get(condition, ""),
        "updated_at": snap.fetched_at,
    }


def roads_card(village, lang):
    rows = list(village.roads.all())
    worst = "open"
    for r in rows:
        if r.status == "closed":
            worst = "closed"
        elif r.status == "limited" and worst != "closed":
            worst = "limited"
    return {
        "summary_status": worst,
        "summary": texts.ROADS_SUMMARY[lang][worst],
        "items": [
            {
                "name": (r.name_ky if lang == "ky" else r.name) or r.name,
                "status": r.status,
                "label": texts.ROAD_STATUS[lang][r.status],
                "note": (r.note_ky if lang == "ky" else r.note) or r.note,
            }
            for r in rows
        ],
    }


def river_card(village, lang):
    since = timezone.now() - timedelta(hours=1)
    reading = (
        Reading.objects.filter(node__village=village, water_level_cm__isnull=False, created_at__gte=since)
        .select_related("node").order_by("-created_at").first()
    )
    if reading is None:
        return {"name": village.river_for(lang), "level_m": None, "status": None, "label": ""}
    limit = reading.node.water_alert_cm or 220.0
    ratio = reading.water_level_cm / limit
    status = "danger" if ratio >= 1 else "watch" if ratio >= 0.7 else "normal"
    return {
        "name": village.river_for(lang),
        "level_m": round(reading.water_level_cm / 100, 1),
        "status": status,
        "label": texts.RIVER[lang][status],
    }


def contacts_card(village, lang):
    out = {"strip": [], "community": [], "transport": None, "support": None}
    for c in village.contacts.all():
        item = {
            "role": c.role,
            "name": (c.name_ky if lang == "ky" else c.name) or c.name,
            "phone": c.phone,
            "phone_display": c.phone_display or c.phone,
        }
        if c.role in (VillageContact.HEAD, VillageContact.AMBULANCE, VillageContact.EMERGENCY):
            out["strip"].append(item)
        elif c.role in (VillageContact.VET, VillageContact.MEDIC, VillageContact.PASTURE):
            out["community"].append(item)
        elif c.role == VillageContact.TRANSPORT:
            out["transport"] = item
        elif c.role == VillageContact.SUPPORT:
            out["support"] = item
    return out


def announcement_card(village, lang):
    a = village.announcements.filter(is_active=True).first()
    if a is None:
        return None
    return {
        "id": a.id,
        "source": (a.source_ky if lang == "ky" else a.source) or a.source,
        "title": (a.title_ky if lang == "ky" else a.title) or a.title,
        "body": (a.body_ky if lang == "ky" else a.body) or a.body,
        "created_at": a.created_at,
    }


def market_count(village):
    qs = Listing.objects.filter(status=Listing.ACTIVE, created_at__gte=timezone.now() - timedelta(days=7))
    if village.valley:
        qs = qs.filter(village__valley=village.valley)
    else:
        qs = qs.filter(village=village)
    return qs.count()


def status_card(village, lang, request):
    level, by_hazard = overall(village)
    alerts = list(Alert.objects.filter(village=village, status=Alert.ACTIVE).select_related("village"))
    alerts.sort(key=lambda a: LEVEL_RANK[a.level], reverse=True)
    for a in alerts:  # manual and report alerts have no risk score behind them
        if LEVEL_RANK[a.level] > LEVEL_RANK[by_hazard[a.hazard]]:
            by_hazard[a.hazard] = a.level
    level = max_level([level, *by_hazard.values()])
    serialized = AlertSerializer(alerts, many=True, context={"request": request}).data
    name = village.name_for(lang)
    if level in (LEVEL_HIGH, "critical") and serialized:
        headline, subline = serialized[0]["title"], serialized[0]["message"]
        tone = "danger"
    elif level == LEVEL_MEDIUM:
        top = max(by_hazard, key=lambda h: LEVEL_RANK[by_hazard[h]])
        headline = texts.WATCH[lang]["headline"].format(hazard=texts.HAZARD_NAMES[lang][top])
        subline = texts.WATCH[lang]["subline"]
        tone = "watch"
    else:
        headline = texts.CALM[lang]["headline"].format(village=name)
        subline = texts.CALM[lang]["subline"]
        tone = "calm"
    return {
        "level": level,
        "tone": tone,
        "hazards": by_hazard,
        "headline": headline,
        "map_headline": texts.CALM[lang]["map_headline"] if tone == "calm" else headline,
        "subline": subline,
        "alerts": serialized,
        "primary_alert": serialized[0] if serialized else None,
        "updated_at": timezone.now(),
    }


def speech_text(village, lang, status, roads, weather, primary_shelter):
    name = village.name_for(lang)
    shelter = primary_shelter["name"] if primary_shelter else ("мектеп" if lang == "ky" else "школа")
    if status["tone"] == "danger" and status["primary_alert"]:
        a = status["primary_alert"]
        return texts.SPEECH_ALERT[lang].format(title=a["title"], body=a["message"], shelter=shelter).replace("\n", " ")
    weather_part = ""
    if weather:
        word = "градус" if lang == "ky" else "градусов"
        weather_part = f"{weather['label']}, {weather['temp_c']} {word}. "
    return texts.SPEECH_CALM[lang].format(
        village=name, roads=roads["summary"], weather=weather_part, shelter=shelter
    )
