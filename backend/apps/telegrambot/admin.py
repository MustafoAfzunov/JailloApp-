from django.contrib import admin

from .models import BotSession


@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "state", "updated_at")
