from django.contrib import admin

from .models import EvacuationPoint, Village


class EvacuationPointInline(admin.TabularInline):
    model = EvacuationPoint
    extra = 0


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "region", "lat", "lon", "population")
    search_fields = ("name", "name_ky", "name_en", "region")
    inlines = [EvacuationPointInline]


@admin.register(EvacuationPoint)
class EvacuationPointAdmin(admin.ModelAdmin):
    list_display = ("name", "village", "lat", "lon", "capacity")
    list_filter = ("village",)
