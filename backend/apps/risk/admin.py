from django.contrib import admin

from .models import FireHotspot, RiskAssessment, RiskHistory, WeatherSnapshot


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("village", "hazard", "level", "score", "eta_seconds", "updated_at")
    list_filter = ("hazard", "level", "village")


@admin.register(RiskHistory)
class RiskHistoryAdmin(admin.ModelAdmin):
    list_display = ("village", "hazard", "level", "score", "created_at")
    list_filter = ("hazard", "level")


@admin.register(FireHotspot)
class FireHotspotAdmin(admin.ModelAdmin):
    list_display = ("latitude", "longitude", "acquired_at", "confidence", "frp", "satellite")
    list_filter = ("confidence", "satellite")
    date_hierarchy = "acquired_at"


@admin.register(WeatherSnapshot)
class WeatherSnapshotAdmin(admin.ModelAdmin):
    list_display = ("village", "fetched_at")
    list_filter = ("village",)
