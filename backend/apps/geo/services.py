from apps.common.geo import haversine_km

from .models import Village


def nearest_village(lat, lon, max_km=50.0):
    """Return the closest Village within max_km, or None."""
    best, best_d = None, None
    for v in Village.objects.all():
        d = haversine_km(lat, lon, v.lat, v.lon)
        if best_d is None or d < best_d:
            best, best_d = v, d
    if best is not None and best_d <= max_km:
        return best
    return None
