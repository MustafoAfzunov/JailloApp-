from rest_framework.routers import DefaultRouter

from .views import HazardReportViewSet

router = DefaultRouter()
router.register("", HazardReportViewSet, basename="report")

urlpatterns = router.urls
