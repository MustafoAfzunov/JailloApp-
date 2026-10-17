from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.constants import pick_lang

from . import services as svc


def _lang(request):
    lang = request.query_params.get("lang")
    if not lang and request.user.is_authenticated:
        lang = request.user.language
    return pick_lang(lang if lang in ("ky", "ru", "en") else "ky")


def _village_block(village, lang):
    return {
        "id": village.id,
        "slug": village.slug,
        "name": village.name_for(lang),
        "valley": village.valley_for(lang),
        "elevation_m": village.elevation_m,
        "lat": village.lat,
        "lon": village.lon,
        "region": village.region,
    }


class ConfigView(APIView):
    """What the app needs before login."""

    permission_classes = [AllowAny]

    def get(self, request):
        from apps.geo.models import Village

        return Response(
            {
                "bot_username": settings.TELEGRAM_BOT_USERNAME,
                "debug_codes": bool(settings.DEBUG and settings.OTP_EXPOSE_IN_DEBUG),
                "villages": [
                    {"id": v.id, "slug": v.slug, "name": v.name_for(_lang(request)), "valley": v.valley_for(_lang(request))}
                    for v in Village.objects.all()
                ],
            }
        )


class HomeView(APIView):
    """Everything the Home screen shows. ?village=<slug>&lang=ky|ru"""

    permission_classes = [AllowAny]

    def get(self, request):
        lang = _lang(request)
        village = svc.pick_village(request.query_params.get("village"), request.user)
        if village is None:
            return Response({"detail": "No villages yet. Run seed_demo."}, status=404)
        origin = svc.origin_for(village, request.user)
        shelter_list = svc.shelters(village, origin, lang)
        status = svc.status_card(village, lang, request)
        weather = svc.weather_card(village, lang)
        roads = svc.roads_card(village, lang)
        primary = shelter_list[0] if shelter_list else None
        return Response(
            {
                "village": _village_block(village, lang),
                "status": status,
                "weather": weather,
                "roads": roads,
                "shelters": {"count": len(shelter_list), "primary": primary},
                "market": {"new_count": svc.market_count(village)},
                "announcement": svc.announcement_card(village, lang),
                "contacts": svc.contacts_card(village, lang),
                "speech": svc.speech_text(village, lang, status, roads, weather, primary),
            }
        )


class MapView(APIView):
    """Everything the Safety-map screen draws. Coordinates are lat/lon; the app projects them."""

    permission_classes = [AllowAny]

    def get(self, request):
        lang = _lang(request)
        village = svc.pick_village(request.query_params.get("village"), request.user)
        if village is None:
            return Response({"detail": "No villages yet. Run seed_demo."}, status=404)
        lat, lon, is_home = svc.origin_for(village, request.user)
        shelter_list = svc.shelters(village, (lat, lon), lang)
        status = svc.status_card(village, lang, request)
        weather = svc.weather_card(village, lang)
        roads = svc.roads_card(village, lang)
        primary = shelter_list[0] if shelter_list else None

        points = [(village.lat, village.lon), (lat, lon)]
        for z in village.zones.all():
            points += [tuple(p) for p in z.polygon]
        for r in village.routes.all():
            points += [tuple(p) for p in r.path]
        points += [(s["lat"], s["lon"]) for s in shelter_list]
        points += [(b.lat, b.lon) for b in village.buildings.all()]
        pad = 0.0015
        bounds = {
            "south": min(p[0] for p in points) - pad, "north": max(p[0] for p in points) + pad,
            "west": min(p[1] for p in points) - pad, "east": max(p[1] for p in points) + pad,
        }
        home = {"lat": lat, "lon": lon, "label": getattr(request.user, "home_label", ""), "is_home": is_home}
        return Response(
            {
                "village": _village_block(village, lang),
                "bounds": bounds,
                "status": status,
                "weather": weather,
                "roads": roads,
                "river": svc.river_card(village, lang),
                "zones": [
                    {"id": z.id, "kind": z.kind, "hazard": z.hazard, "name": z.name_for(lang), "polygon": z.polygon}
                    for z in village.zones.all()
                ],
                "routes": [{"id": r.id, "point": r.point_id, "path": r.path} for r in village.routes.all()],
                "buildings": [{"id": b.id, "label": b.label, "lat": b.lat, "lon": b.lon} for b in village.buildings.all()],
                "shelters": shelter_list,
                "home": home if request.user.is_authenticated else None,
                "contacts": svc.contacts_card(village, lang),
                "speech": svc.speech_text(village, lang, status, roads, weather, primary),
            }
        )
