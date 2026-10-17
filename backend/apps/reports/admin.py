from django.contrib import admin

from .models import HazardReport


@admin.register(HazardReport)
class HazardReportAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "village", "user", "status", "crowd_confirmed", "source", "created_at")
    list_filter = ("status", "type", "source", "crowd_confirmed", "village")
    date_hierarchy = "created_at"
