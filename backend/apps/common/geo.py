"""Small geo helpers (no GIS dependency)."""
import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bbox(lat, lon, radius_km):
    """Return (min_lat, max_lat, min_lon, max_lon) around a point."""
    d_lat = radius_km / 111.0
    d_lon = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    return lat - d_lat, lat + d_lat, lon - d_lon, lon + d_lon
