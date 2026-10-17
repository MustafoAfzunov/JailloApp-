from rest_framework import serializers

from .models import User, WatchedLocation
from .phone import normalize_phone


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except ValueError:
            raise serializers.ValidationError("Enter a valid phone number.") from None


class OTPRequestSerializer(serializers.Serializer):
    phone = PhoneField()


class OTPVerifySerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.CharField(min_length=4, max_length=8)
    name = serializers.CharField(required=False, allow_blank=True, max_length=120)


class UserSerializer(serializers.ModelSerializer):
    telegram_linked = serializers.SerializerMethodField()
    village_name = serializers.CharField(source="village.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id", "phone", "name", "role", "village", "village_name",
            "language", "telegram_linked", "is_verified", "home_lat", "home_lon", "home_label",
        ]
        read_only_fields = ["id", "phone", "role", "is_verified"]

    def get_telegram_linked(self, obj):
        return bool(obj.telegram_chat_id)


class WatchedLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchedLocation
        fields = ["id", "name", "lat", "lon", "radius_km"]

    def validate_radius_km(self, value):
        if not 0.5 <= value <= 100:
            raise serializers.ValidationError("Radius must be between 0.5 and 100 km.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None and request.user.watched_locations.count() >= 10:
            raise serializers.ValidationError("You can watch at most 10 locations.")
        return attrs
