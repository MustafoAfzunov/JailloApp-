from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.alerts.serializers import AlertSerializer
from apps.common.constants import HAZARDS, LEVEL_LOW, max_level, pick_lang
from apps.common.geo import bbox, haversine_km
from apps.common.permissions import IsRescuerOrAdmin
from apps.geo.models import Village
from apps.geo.serializers import EvacuationPointSerializer
from apps.sensors.models import Node
from apps.sensors.serializers import NodeSerializer

from . import engine, firms, weather
from .models import FireHotspot, RiskAssessment, RiskHistory
from .serializers import FireHotspotSerializer, RiskAssessmentSerializer, RiskHistorySerializer


def _hazard_map(village):
    """{hazard: assessment dict}; hazards never evaluated show as low."""
    current = {a.hazard: RiskAssessmentSerializer(a).data for a in village.assessments.all()}
    for h in HAZARDS:
        current.setdefault(h, {"hazard": h, "level": LEVEL_LOW, "score": 0, "eta_seconds": None, "details": {}})
    return current


class OverviewView(APIView):
    """Map overview: every village with its overall level and per-hazard levels. ?lang=ru|ky|en"""

    permission_classes = [AllowAny]

    def get(self, request):
        lang = pick_lang(request.query_params.get("lang"))
        data = []
        for v in Village.objects.prefetch_related("assessments"):
            hazards = _hazard_map(v)
            data.append(
                {
                    "id": v.id, "slug": v.slug, "name": v.name_for(lang), "region": v.region,
                    "lat": v.lat, "lon": v.lon,
                    "overall_level": max_level(h["level"] for h in hazards.values()),
                    "hazards": {h: hazards[h]["level"] for h in HAZARDS},
                }
            )
        return Response(data)


class VillageRiskView(APIView):
    """Everything the Home and Hazard-detail screens need for one village."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        village = get_object_or_404(Village.objects.prefetch_related("evacuation_points", "assessments"), pk=pk)
        hazards = _hazard_map(village)
        now = timezone.now()

        lat_min, lat_max, lon_min, lon_max = bbox(village.lat, village.lon, 25)
        hotspots = FireHotspot.objects.filter(
            acquired_at__gte=now - timedelta(hours=48),
            latitude__range=(lat_min, lat_max),
            longitude__range=(lon_min, lon_max),
        ).exclude(confidence="low")[:100]

        alerts = Alert.objects.filter(village=village, status=Alert.ACTIVE).select_related("village")
        nodes = Node.objects.filter(village=village, is_active=True)
        return Response(
            {
                "village": {"id": village.id, "slug": village.slug, "name": village.name,
                            "name_ky": village.name_ky, "name_en": village.name_en,
                            "lat": village.lat, "lon": village.lon},
                "overall_level": max_level(h["level"] for h in hazards.values()),
                "hazards": hazards,
                "active_alerts": AlertSerializer(alerts, many=True, context={"request": request}).data,
                "nodes": NodeSerializer(nodes, many=True).data,
                "weather": weather.latest_weather(village, max_age_hours=6),
                "fire_hotspots": [
                    {**FireHotspotSerializer(h).data,
                     "distance_km": round(haversine_km(village.lat, village.lon, h.latitude, h.longitude), 1)}
                    for h in hotspots
                ],
                "evacuation_points": EvacuationPointSerializer(village.evacuation_points.all(), many=True).data,
            }
        )


class VillageHistoryView(ListAPIView):
    """Level changes over time. ?hazard=fire&days=7"""

    permission_classes = [AllowAny]
    serializer_class = RiskHistorySerializer
    pagination_class = None

    def get_queryset(self):
        qs = RiskHistory.objects.filter(village_id=self.kwargs["pk"])
        hazard = self.request.query_params.get("hazard")
        if hazard in HAZARDS:
            qs = qs.filter(hazard=hazard)
        try:
            days = min(90, max(1, int(self.request.query_params.get("days", 7))))
        except ValueError:
            days = 7
        return qs.filter(created_at__gte=timezone.now() - timedelta(days=days))[:500]


class FireHotspotListView(ListAPIView):
    """Recent satellite hotspots. ?hours=48&bbox=west,south,east,north"""

    permission_classes = [AllowAny]
    serializer_class = FireHotspotSerializer
    pagination_class = None

    def get_queryset(self):
        try:
            hours = min(120, max(1, int(self.request.query_params.get("hours", 48))))
        except ValueError:
            hours = 48
        qs = FireHotspot.objects.filter(acquired_at__gte=timezone.now() - timedelta(hours=hours)).exclude(confidence="low")
        box = self.request.query_params.get("bbox")
        if box:
            try:
                w, s, e, n = (float(x) for x in box.split(","))
                qs = qs.filter(longitude__range=(w, e), latitude__range=(s, n))
            except ValueError:
                pass
        return qs[:1000]


class RefreshView(APIView):
    """Rescuers: recompute risk now. Body: {"village": id (optional), "external": true to pull weather + FIRMS first}."""

    permission_classes = [IsRescuerOrAdmin]

    def post(self, request):
        warnings = []
        villages = Village.objects.all()
        if request.data.get("village"):
            villages = villages.filter(pk=request.data["village"])
        if request.data.get("external"):
            for v in villages:
                try:
                    weather.refresh_weather(v)
                except weather.WeatherError as exc:
                    warnings.append(f"{v.slug}: {exc}")
            try:
                firms.refresh_hotspots()
            except firms.FirmsError as exc:
                warnings.append(str(exc))
        summary = {}
        for v in villages:
            results = engine.evaluate_village(v)
            summary[v.slug] = {r.hazard: {"level": r.level, "score": round(r.score, 1)} for r in results}
        return Response({"evaluated": summary, "warnings": warnings})
