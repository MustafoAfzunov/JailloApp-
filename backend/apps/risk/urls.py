from django.urls import path

from .views import (
    FireHotspotListView,
    OverviewView,
    RefreshView,
    VillageHistoryView,
    VillageRiskView,
)

urlpatterns = [
    path("overview/", OverviewView.as_view(), name="risk-overview"),
    path("villages/<int:pk>/", VillageRiskView.as_view(), name="risk-village"),
    path("villages/<int:pk>/history/", VillageHistoryView.as_view(), name="risk-history"),
    path("fire-hotspots/", FireHotspotListView.as_view(), name="fire-hotspots"),
    path("refresh/", RefreshView.as_view(), name="risk-refresh"),
]
