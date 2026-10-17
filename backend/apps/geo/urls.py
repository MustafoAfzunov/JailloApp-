from rest_framework.routers import DefaultRouter

from .views import EvacuationPointViewSet, VillageViewSet

router = DefaultRouter()
router.register("villages", VillageViewSet, basename="village")
router.register("evacuation-points", EvacuationPointViewSet, basename="evacuation-point")

urlpatterns = router.urls
