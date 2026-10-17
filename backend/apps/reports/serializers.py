from rest_framework import serializers

from .models import HazardReport


class HazardReportSerializer(serializers.ModelSerializer):
    village_name = serializers.CharField(source="village.name", read_only=True, default=None)
    reporter = serializers.SerializerMethodField()

    class Meta:
        model = HazardReport
        fields = [
            "id", "type", "description", "photo", "lat", "lon", "village", "village_name",
            "status", "source", "crowd_confirmed", "reporter", "created_at",
        ]
        read_only_fields = ["id", "village", "status", "source", "crowd_confirmed", "created_at"]

    def get_reporter(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated and getattr(request.user, "is_rescuer", False):
            return {"id": obj.user_id, "name": obj.user.name, "phone": obj.user.phone}
        return None

    def validate_photo(self, value):
        if value and value.size > 8 * 1024 * 1024:
            raise serializers.ValidationError("Photo must be under 8 MB.")
        return value

    def validate_lat(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Invalid latitude.")
        return value

    def validate_lon(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Invalid longitude.")
        return value
