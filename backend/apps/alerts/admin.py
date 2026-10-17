from django.contrib import admin

from .models import Alert, AlertDelivery, SafeCheckin, SirenCommand


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "village", "hazard", "level", "status", "source", "is_simulated", "created_at")
    list_filter = ("status", "hazard", "level", "source", "village")
    readonly_fields = ("texts", "details")


@admin.register(AlertDelivery)
class AlertDeliveryAdmin(admin.ModelAdmin):
    list_display = ("alert", "user", "level", "channel", "status", "created_at")
    list_filter = ("status", "channel")


@admin.register(SafeCheckin)
class SafeCheckinAdmin(admin.ModelAdmin):
    list_display = ("alert", "user", "created_at")


@admin.register(SirenCommand)
class SirenCommandAdmin(admin.ModelAdmin):
    list_display = ("village", "alert", "action", "created_at", "acked_at")
    list_filter = ("action", "village")
