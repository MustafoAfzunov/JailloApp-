from django.utils import timezone
from rest_framework import serializers

from apps.common.constants import HAZARD_CHOICES, LEVEL_CHOICES, pick_lang
from apps.geo.models import Village

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    """Alert with texts in the requested language (?lang=ru|ky|en, default: user's language)."""

    village_name = serializers.CharField(source="village.name", read_only=True)
    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    eta_seconds_remaining = serializers.SerializerMethodField()
    safe_count = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            "id", "village", "village_name", "hazard", "level", "status", "source", "is_simulated",
            "title", "message", "texts", "details", "eta_at", "eta_seconds_remaining",
            "safe_count", "created_at", "updated_at", "resolved_at",
        ]

    def _lang(self):
        request = self.context.get("request")
        lang = request.query_params.get("lang") if request else None
        if not lang and request and request.user and request.user.is_authenticated:
            lang = getattr(request.user, "language", None)
        return pick_lang(lang)

    def _text(self, obj, key):
        return (obj.texts.get(self._lang()) or obj.texts.get("ru") or {}).get(key, "")

    def get_title(self, obj):
        return self._text(obj, "title")

    def get_message(self, obj):
        return self._text(obj, "body")

    def get_eta_seconds_remaining(self, obj):
        if obj.eta_at is None or obj.status != Alert.ACTIVE:
            return None
        return max(0, int((obj.eta_at - timezone.now()).total_seconds()))

    def get_safe_count(self, obj):
        return obj.checkins.count()


class ManualAlertSerializer(serializers.Serializer):
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    hazard = serializers.ChoiceField(choices=HAZARD_CHOICES)
    level = serializers.ChoiceField(choices=LEVEL_CHOICES)
    eta_seconds = serializers.IntegerField(required=False, min_value=0, max_value=86400)


class SafeCheckinSerializer(serializers.Serializer):
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
