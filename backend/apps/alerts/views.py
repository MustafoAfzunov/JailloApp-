from datetime import timedelta

from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsRescuerOrAdmin
from apps.sensors.authentication import DeviceKeyAuthentication, IsDevice

from . import services
from .models import Alert, SafeCheckin, SirenCommand
from .serializers import AlertSerializer, ManualAlertSerializer, SafeCheckinSerializer


class AlertFilter(filters.FilterSet):
    since = filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gte")

    class Meta:
        model = Alert
        fields = ["village", "hazard", "level", "status", "source", "since"]


class AlertViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Public alert feed. Rescuers can create, resolve and dismiss alerts."""

    queryset = Alert.objects.select_related("village").prefetch_related("checkins")
    serializer_class = AlertSerializer
    permission_classes = [AllowAny]
    filterset_class = AlertFilter
    ordering_fields = ["created_at", "updated_at"]

    @action(detail=False, methods=["get"], pagination_class=None)
    def active(self, request):
        """Active alerts (add ?village=<id> for one village). Poll this every few seconds."""
        qs = self.filter_queryset(self.get_queryset()).filter(status=Alert.ACTIVE)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="create", permission_classes=[IsRescuerOrAdmin])
    def create_manual(self, request):
        """Rescuer: raise an alert by hand. Body: village, hazard, level, eta_seconds?"""
        s = ManualAlertSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        alert = services.raise_manual_alert(
            d["village"], d["hazard"], d["level"], user=request.user, eta_seconds=d.get("eta_seconds")
        )
        return Response(self.get_serializer(alert).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[IsRescuerOrAdmin])
    def simulate(self, request):
        """Demo trigger: same as create_manual but flagged [DEMO] so nobody mistakes it for real."""
        s = ManualAlertSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        alert = services.raise_manual_alert(
            d["village"], d["hazard"], d["level"], user=request.user, source=Alert.SOURCE_SIM,
            eta_seconds=d.get("eta_seconds"), simulated=True,
        )
        return Response(self.get_serializer(alert).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsRescuerOrAdmin])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        if alert.status == Alert.ACTIVE:
            services.resolve_alert(alert, Alert.RESOLVED, by=request.user)
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=["post"], permission_classes=[IsRescuerOrAdmin])
    def dismiss(self, request, pk=None):
        """Mark as a false alarm."""
        alert = self.get_object()
        if alert.status == Alert.ACTIVE:
            services.resolve_alert(alert, Alert.DISMISSED, by=request.user)
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def safe(self, request, pk=None):
        """The 'I'm safe' button. Optional body: lat, lon."""
        alert = self.get_object()
        s = SafeCheckinSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        SafeCheckin.objects.update_or_create(alert=alert, user=request.user, defaults=s.validated_data)
        return Response({"ok": True, "safe_count": alert.checkins.count()})

    @action(detail=True, methods=["get"], permission_classes=[IsRescuerOrAdmin])
    def checkins(self, request, pk=None):
        alert = self.get_object()
        return Response(
            [
                {"user": c.user.name or c.user.phone, "lat": c.lat, "lon": c.lon, "created_at": c.created_at}
                for c in alert.checkins.select_related("user")
            ]
        )


class SirenPendingView(APIView):
    """Village gateway node: fetch unacknowledged siren commands. Auth: X-Device-Key."""

    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [IsDevice]
    throttle_scope = "ingest"

    def get(self, request):
        node = request.auth
        # commands from the last day only, so an old backlog never fires a siren
        cmds = SirenCommand.objects.filter(
            village=node.village, acked_at__isnull=True, created_at__gte=timezone.now() - timedelta(days=1)
        )
        return Response([{"id": c.id, "action": c.action, "alert": c.alert_id} for c in cmds])


class SirenAckView(APIView):
    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [IsDevice]
    throttle_scope = "ingest"

    def post(self, request, pk):
        updated = SirenCommand.objects.filter(
            pk=pk, village=request.auth.village, acked_at__isnull=True
        ).update(acked_at=timezone.now())
        return Response({"acked": bool(updated)})
