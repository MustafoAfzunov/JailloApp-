from rest_framework import serializers

from .models import EvacuationPoint, Village


class EvacuationPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvacuationPoint
        fields = ["id", "village", "name", "lat", "lon", "notes", "capacity"]


class VillageSerializer(serializers.ModelSerializer):
    evacuation_points = EvacuationPointSerializer(many=True, read_only=True)

    class Meta:
        model = Village
        fields = [
            "id", "slug", "name", "name_ky", "name_en", "region",
            "lat", "lon", "population", "evacuation_points",
        ]
