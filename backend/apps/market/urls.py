from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ListingViewSet, OrderViewSet, ThreadViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("listings", ListingViewSet, basename="listing")
router.register("orders", OrderViewSet, basename="order")
router.register("threads", ThreadViewSet, basename="thread")

urlpatterns = router.urls
