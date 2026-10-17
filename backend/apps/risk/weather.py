"""Open-Meteo client (free, no API key) and summary used by the risk engine."""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

import requests
from django.conf import settings
from django.utils import timezone

from .models import WeatherSnapshot

log = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = "precipitation,snowfall,temperature_2m,wind_speed_10m,snow_depth,freezing_level_height,weather_code"


class WeatherError(Exception):
    pass


def fetch_open_meteo(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": HOURLY,
        "past_days": 2,
        "forecast_days": 2,
        "timezone": "UTC",
    }
    try:
        resp = requests.get(URL, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherError(f"Open-Meteo request failed ({exc.__class__.__name__})") from None


def condition_from_code(code):
    """WMO weather code -> a small set of conditions the UI has icons for."""
    if code is None:
        return None
    code = int(code)
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly_cloudy"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code >= 95:
        return "storm"
    return "cloudy"


def _num(value, default=0.0):
    return default if value is None else float(value)


def parse_open_meteo(data, now=None):
    """Reduce hourly arrays to the numbers the risk engine uses (UTC, relative to `now`)."""
    now = (now or timezone.now()).astimezone(dt_timezone.utc)
    hourly = data.get("hourly") or {}
    times = [
        datetime.fromisoformat(t).replace(tzinfo=dt_timezone.utc) for t in hourly.get("time", [])
    ]
    if not times:
        raise WeatherError("Open-Meteo returned no hourly data")

    def series(name):
        return hourly.get(name) or [None] * len(times)

    precip, snow, temp = series("precipitation"), series("snowfall"), series("temperature_2m")
    wind, depth, freeze = series("wind_speed_10m"), series("snow_depth"), series("freezing_level_height")
    wcode = series("weather_code")

    start_prev, end_next = now - timedelta(hours=24), now + timedelta(hours=24)
    prev_idx = [i for i, t in enumerate(times) if start_prev < t <= now]
    next_idx = [i for i, t in enumerate(times) if now < t <= end_next]
    now_idx = max((i for i, t in enumerate(times) if t <= now), default=0)

    return {
        "precip_prev24_mm": round(sum(_num(precip[i]) for i in prev_idx), 1),
        "precip_next24_mm": round(sum(_num(precip[i]) for i in next_idx), 1),
        "snowfall_prev24_cm": round(sum(_num(snow[i]) for i in prev_idx), 1),
        "snowfall_next24_cm": round(sum(_num(snow[i]) for i in next_idx), 1),
        "temp_now_c": round(_num(temp[now_idx]), 1),
        "temp_max_prev24_c": round(max((_num(temp[i], -99) for i in prev_idx), default=_num(temp[now_idx])), 1),
        "wind_max_24h_kmh": round(
            max((_num(wind[i]) for i in prev_idx + next_idx), default=0.0), 1
        ),
        "snow_depth_m": round(_num(depth[now_idx]), 2),
        "freezing_level_m": round(_num(freeze[now_idx]), 0),
        "condition": condition_from_code(wcode[now_idx]),
    }


def refresh_weather(village):
    snapshot = WeatherSnapshot.objects.create(
        village=village, summary=parse_open_meteo(fetch_open_meteo(village.lat, village.lon))
    )
    # keep the table small: drop snapshots older than 3 days
    WeatherSnapshot.objects.filter(
        village=village, fetched_at__lt=timezone.now() - timedelta(days=3)
    ).delete()
    return snapshot


def latest_weather(village, max_age_hours=3):
    snap = village.weather.first()
    if snap and snap.fetched_at >= timezone.now() - timedelta(hours=max_age_hours):
        return snap.summary
    return None


def weather_is_fresh(village):
    snap = village.weather.first()
    return bool(
        snap and snap.fetched_at >= timezone.now() - timedelta(minutes=settings.WEATHER_CACHE_MINUTES)
    )
