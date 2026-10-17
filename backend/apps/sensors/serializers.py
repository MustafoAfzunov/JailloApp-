from rest_framework import serializers

from .models import Node, Reading, VibrationEvent


class IngestSerializer(serializers.Serializer):
    """Payload a sensor node posts. Every field is optional; send what the node measures."""

    vibration_rms = serializers.FloatField(required=False, min_value=0, max_value=1000)
    dominant_freq_hz = serializers.FloatField(required=False, min_value=0, max_value=5000)
    samples = serializers.ListField(
        child=serializers.FloatField(), required=False, max_length=4096
    )
    sample_rate_hz = serializers.FloatField(required=False, min_value=10, max_value=8000)
    water_level_cm = serializers.FloatField(required=False, min_value=0, max_value=5000)
    rain_mm = serializers.FloatField(required=False, min_value=0, max_value=500)
    smoke_ppm = serializers.FloatField(required=False, min_value=0, max_value=100000)
    temperature_c = serializers.FloatField(required=False, min_value=-80, max_value=150)
    humidity = serializers.FloatField(required=False, min_value=0, max_value=100)
    battery_v = serializers.FloatField(required=False, min_value=0, max_value=30)
    crackle_score = serializers.FloatField(required=False, min_value=0, max_value=1)
    edge_class = serializers.ChoiceField(
        required=False, choices=["mudflow", "earthquake", "vehicle", "noise"]
    )
    edge_confidence = serializers.FloatField(required=False, min_value=0, max_value=1)


class ReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reading
        fields = [
            "id", "created_at", "vibration_rms", "dominant_freq_hz", "water_level_cm",
            "rain_mm", "smoke_ppm", "temperature_c", "battery_v",
        ]


class NodeSerializer(serializers.ModelSerializer):
    village_name = serializers.CharField(source="village.name", read_only=True)
    status = serializers.CharField(read_only=True)
    latest = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            "id", "device_id", "name", "village", "village_name", "kind", "lat", "lon",
            "flow_order", "battery_v", "last_seen", "status", "latest",
        ]

    def get_latest(self, obj):
        reading = obj.readings.first()
        return ReadingSerializer(reading).data if reading else None


class VibrationEventSerializer(serializers.ModelSerializer):
    node_device_id = serializers.CharField(source="node.device_id", read_only=True)

    class Meta:
        model = VibrationEvent
        fields = [
            "id", "node", "node_device_id", "classification", "confidence",
            "rms", "dominant_freq_hz", "created_at",
        ]
