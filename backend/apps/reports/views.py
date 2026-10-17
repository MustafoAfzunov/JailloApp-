from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.alerts.serializers import AlertSerializer
from apps.common.permissions import IsRescuerOrAdmin

from . import services
from .models import HazardReport
from .serializers import HazardReportSerializer


class HazardReportViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Citizens send hazard reports (photo + GPS). Rescuers see all reports and confirm or dismiss them."""

    serializer_class = HazardReportSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = "report"
    filterset_fields = ["status", "type", "village"]

    def get_throttles(self):
        if self.action == "create":
            return [ScopedRateThrottle()]
        return []

    def get_queryset(self):
        qs = HazardReport.objects.select_related("village", "user")
        user = self.request.user
        return qs if getattr(user, "is_rescuer", False) else qs.filter(user=user)

    def perform_create(self, serializer):
        report = serializer.save(user=self.request.user)
        services.after_create(report)

    def _review(self, request, status_value):
        report = self.get_object()
        alert = services.review(report, request.user, status_value)
        data = self.get_serializer(report).data
        if alert is not None:
            data["alert"] = AlertSerializer(alert, context={"request": request}).data
        return Response(data)

    @action(detail=True, methods=["post"], permission_classes=[IsRescuerOrAdmin])
    def confirm(self, request, pk=None):
        """Confirm the report: raises a High alert for the village."""
        return self._review(request, HazardReport.CONFIRMED)

    @action(detail=True, methods=["post"], permission_classes=[IsRescuerOrAdmin])
    def dismiss(self, request, pk=None):
        return self._review(request, HazardReport.DISMISSED)
