from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AlertViewSet, SirenAckView, SirenPendingView

router = SimpleRouter()
router.register("", AlertViewSet, basename="alert")

urlpatterns = [
    path("siren/pending/", SirenPendingView.as_view(), name="siren-pending"),
    path("siren/<int:pk>/ack/", SirenAckView.as_view(), name="siren-ack"),
] + router.urls
