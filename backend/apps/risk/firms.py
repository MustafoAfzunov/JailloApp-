"""NASA FIRMS (satellite fire hotspots) client. Needs a free MAP_KEY."""
import csv
import io
import logging
from datetime import datetime, timezone as dt_timezone

import requests
from django.conf import settings

from .models import FireHotspot

log = logging.getLogger(__name__)

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


class FirmsError(Exception):
    pass


def fetch_csv(bbox=None, source=None, days=None):
    key = settings.NASA_FIRMS_MAP_KEY
    if not key:
        raise FirmsError("NASA_FIRMS_MAP_KEY is not set")
    bbox = bbox or settings.FIRMS_BBOX
    source = source or settings.NASA_FIRMS_SOURCE
    days = days or settings.FIRMS_DAY_RANGE
    url = f"{BASE}/{key}/{source}/{bbox}/{days}"
    try:
        resp = requests.get(url, timeout=40)
        resp.raise_for_status()
    except requests.RequestException as exc:
        # Do not chain: the exception text contains the URL with the key.
        raise FirmsError(f"FIRMS request failed ({exc.__class__.__name__})") from None
    return resp.text


def _norm_confidence(raw):
    raw = (raw or "").strip().lower()
    if raw in ("l", "low"):
        return "low"
    if raw in ("h", "high"):
        return "high"
    if raw in ("n", "nominal"):
        return "nominal"
    try:  # MODIS gives a number 0-100
        value = float(raw)
        return "low" if value < 30 else ("nominal" if value < 80 else "high")
    except ValueError:
        return "nominal"


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_csv(text, source=""):
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if "latitude" not in first_line.lower():
        raise FirmsError(f"Unexpected FIRMS response: {first_line[:80] or 'empty'}")
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            acquired = datetime.strptime(
                f"{row['acq_date']} {row['acq_time'].zfill(4)}", "%Y-%m-%d %H%M"
            ).replace(tzinfo=dt_timezone.utc)
            lat, lon = float(row["latitude"]), float(row["longitude"])
        except (KeyError, ValueError):
            continue
        rows.append(
            {
                "latitude": lat,
                "longitude": lon,
                "acquired_at": acquired,
                "satellite": row.get("satellite", "")[:20],
                "confidence": _norm_confidence(row.get("confidence")),
                "frp": _float(row.get("frp")),
                "brightness": _float(row.get("bright_ti4") or row.get("brightness")),
                "source": source,
            }
        )
    return rows


def store_hotspots(rows):
    before = FireHotspot.objects.count()
    FireHotspot.objects.bulk_create([FireHotspot(**r) for r in rows], ignore_conflicts=True)
    return FireHotspot.objects.count() - before


def refresh_hotspots():
    source = settings.NASA_FIRMS_SOURCE
    rows = parse_csv(fetch_csv(), source=source)
    return len(rows), store_hotspots(rows)
