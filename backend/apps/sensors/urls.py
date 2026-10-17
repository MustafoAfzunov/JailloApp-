from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import IngestView, NodeViewSet, VibrationEventViewSet

router = DefaultRouter()
router.register("nodes", NodeViewSet, basename="node")
router.register("vibration-events", VibrationEventViewSet, basename="vibration-event")

urlpatterns = [path("ingest/", IngestView.as_view(), name="ingest")] + router.urls
