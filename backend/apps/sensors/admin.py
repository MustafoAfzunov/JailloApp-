from django.contrib import admin, messages

from .models import Node, Reading, VibrationEvent


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("device_id", "name", "village", "kind", "flow_order", "status", "battery_v", "last_seen", "is_active")
    list_filter = ("village", "kind", "is_active")
    search_fields = ("device_id", "name")
    readonly_fields = ("key_prefix", "last_seen", "battery_v")
    actions = ["rotate_keys"]

    def save_model(self, request, obj, form, change):
        key = None
        if not change:
            key = obj.rotate_key(save=False)
        super().save_model(request, obj, form, change)
        if key:
            messages.warning(request, f"Device key for {obj.device_id} (shown once, copy it now): {key}")

    @admin.action(description="Issue a new device key (old key stops working)")
    def rotate_keys(self, request, queryset):
        for node in queryset:
            key = node.rotate_key()
            messages.warning(request, f"New key for {node.device_id} (shown once): {key}")


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ("node", "created_at", "vibration_rms", "water_level_cm", "smoke_ppm", "temperature_c")
    list_filter = ("node",)
    date_hierarchy = "created_at"


@admin.register(VibrationEvent)
class VibrationEventAdmin(admin.ModelAdmin):
    list_display = ("node", "classification", "confidence", "rms", "created_at")
    list_filter = ("classification", "node")
