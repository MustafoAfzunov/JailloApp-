from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import EvacuationPoint, Village
from .serializers import EvacuationPointSerializer, VillageSerializer


class VillageViewSet(viewsets.ReadOnlyModelViewSet):
    """Public list of villages with their evacuation points."""

    queryset = Village.objects.prefetch_related("evacuation_points")
    serializer_class = VillageSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["region"]
    search_fields = ["name", "name_ky", "name_en", "region"]
    ordering_fields = ["name", "region"]
    pagination_class = None


class EvacuationPointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EvacuationPoint.objects.select_related("village")
    serializer_class = EvacuationPointSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["village"]
    pagination_class = None
