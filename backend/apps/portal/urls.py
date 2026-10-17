from django.urls import path

from .views import ConfigView, HomeView, MapView

urlpatterns = [
    path("config/", ConfigView.as_view()),
    path("home/", HomeView.as_view()),
    path("map/", MapView.as_view()),
]
