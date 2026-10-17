from rest_framework import serializers

from .models import FireHotspot, RiskAssessment, RiskHistory


class RiskAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAssessment
        fields = ["hazard", "level", "score", "eta_seconds", "details", "level_since", "updated_at"]


class RiskHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskHistory
        fields = ["hazard", "level", "score", "created_at"]


class FireHotspotSerializer(serializers.ModelSerializer):
    class Meta:
        model = FireHotspot
        fields = ["id", "latitude", "longitude", "acquired_at", "confidence", "frp", "satellite"]
