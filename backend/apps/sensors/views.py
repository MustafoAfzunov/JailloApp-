from datetime import timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .authentication import DeviceKeyAuthentication, IsDevice
from .models import Node, VibrationEvent
from .serializers import (
    IngestSerializer,
    NodeSerializer,
    ReadingSerializer,
    VibrationEventSerializer,
)


class IngestView(APIView):
    """Sensor nodes post readings here. Auth: `X-Device-Key: <key>` header."""

    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [IsDevice]
    throttle_scope = "ingest"
    serializer_class = IngestSerializer

    def post(self, request):
        s = IngestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        reading, event = services.ingest(request.auth, s.validated_data)
        return Response(
            {
                "ok": True,
                "reading_id": reading.id,
                "classification": event.classification if event else None,
                "confidence": event.confidence if event else None,
            },
            status=status.HTTP_201_CREATED,
        )


class NodeViewSet(viewsets.ReadOnlyModelViewSet):
    """Public node list for the map: position, status, battery and latest reading."""

    queryset = Node.objects.filter(is_active=True).select_related("village")
    serializer_class = NodeSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["village", "kind"]
    pagination_class = None

    @action(detail=True, methods=["get"])
    def readings(self, request, pk=None):
        """Recent readings for charts. ?hours=6 (max 72)"""
        node = self.get_object()
        try:
            hours = min(72, max(1, int(request.query_params.get("hours", 6))))
        except ValueError:
            hours = 6
        qs = node.readings.filter(created_at__gte=timezone.now() - timedelta(hours=hours))
        return Response(ReadingSerializer(qs.order_by("created_at")[:2000], many=True).data)


class VibrationEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VibrationEventSerializer
    permission_classes = [AllowAny]
    filterset_fields = {"node": ["exact"], "node__village": ["exact"], "classification": ["exact"]}

    def get_queryset(self):
        qs = VibrationEvent.objects.select_related("node")
        try:
            hours = min(168, max(1, int(self.request.query_params.get("hours", 24))))
        except ValueError:
            hours = 24
        return qs.filter(created_at__gte=timezone.now() - timedelta(hours=hours))
