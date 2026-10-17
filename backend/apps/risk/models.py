from django.db import models
from django.utils import timezone

from apps.common.constants import HAZARD_CHOICES, LEVEL_CHOICES, LEVEL_LOW


class RiskAssessment(models.Model):
    """Current risk per village and hazard (one row each, updated in place)."""

    village = models.ForeignKey("geo.Village", related_name="assessments", on_delete=models.CASCADE)
    hazard = models.CharField(max_length=12, choices=HAZARD_CHOICES)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_LOW)
    score = models.FloatField(default=0)
    details = models.JSONField(default=dict, blank=True)
    eta_seconds = models.IntegerField(null=True, blank=True)
    level_since = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["village", "hazard"], name="uniq_risk_village_hazard")]
        ordering = ["village", "hazard"]

    def __str__(self):
        return f"{self.village} {self.hazard}: {self.level}"


class RiskHistory(models.Model):
    """Appended whenever a village's level for a hazard changes."""

    village = models.ForeignKey("geo.Village", related_name="risk_history", on_delete=models.CASCADE)
    hazard = models.CharField(max_length=12, choices=HAZARD_CHOICES)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class FireHotspot(models.Model):
    """Satellite fire detection from NASA FIRMS."""

    latitude = models.FloatField()
    longitude = models.FloatField()
    acquired_at = models.DateTimeField(db_index=True)
    satellite = models.CharField(max_length=20, blank=True)
    confidence = models.CharField(max_length=10, default="nominal")  # low / nominal / high
    frp = models.FloatField(null=True, blank=True, help_text="Fire radiative power, MW")
    brightness = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["-acquired_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["latitude", "longitude", "acquired_at", "satellite"], name="uniq_firms_hotspot"
            )
        ]


class WeatherSnapshot(models.Model):
    village = models.ForeignKey("geo.Village", related_name="weather", on_delete=models.CASCADE)
    fetched_at = models.DateTimeField(default=timezone.now, db_index=True)
    summary = models.JSONField(default=dict)

    class Meta:
        ordering = ["-fetched_at"]
