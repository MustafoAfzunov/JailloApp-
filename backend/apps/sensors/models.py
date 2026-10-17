import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class Node(models.Model):
    MULTI, GEOPHONE, WATER, FIRE, GATEWAY = "multi", "geophone", "water", "fire", "gateway"
    KIND_CHOICES = [
        (MULTI, "Geophone + water + rain"),
        (GEOPHONE, "Geophone only"),
        (WATER, "Water level"),
        (FIRE, "Smoke / temperature"),
        (GATEWAY, "LoRa gateway / siren"),
    ]

    device_id = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    village = models.ForeignKey("geo.Village", related_name="nodes", on_delete=models.CASCADE)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=MULTI)
    lat = models.FloatField()
    lon = models.FloatField()
    elevation_m = models.FloatField(null=True, blank=True)
    flow_order = models.SmallIntegerField(
        default=0, help_text="Position along the river toward the village. 0 = most upstream."
    )
    water_alert_cm = models.FloatField(
        null=True, blank=True, help_text="Water level (cm) at which flooding starts"
    )
    api_key_hash = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    key_prefix = models.CharField(max_length=8, blank=True, editable=False)
    battery_v = models.FloatField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["village", "flow_order", "device_id"]

    def __str__(self):
        return f"{self.device_id} ({self.village})"

    def rotate_key(self, save=True) -> str:
        """Create a new device key. The plain key is returned once and never stored."""
        key = "jk_" + secrets.token_urlsafe(30)
        self.api_key_hash = hash_key(key)
        self.key_prefix = key[:7]
        if save and self.pk:
            self.save(update_fields=["api_key_hash", "key_prefix"])
        return key

    @property
    def status(self) -> str:
        if self.last_seen is None:
            return "never"
        age = (timezone.now() - self.last_seen).total_seconds()
        if age <= settings.NODE_OFFLINE_AFTER_SECONDS:
            return "online"
        if age <= settings.NODE_STALE_AFTER_SECONDS:
            return "stale"
        return "offline"


class Reading(models.Model):
    node = models.ForeignKey(Node, related_name="readings", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    vibration_rms = models.FloatField(null=True, blank=True)
    dominant_freq_hz = models.FloatField(null=True, blank=True)
    water_level_cm = models.FloatField(null=True, blank=True)
    rain_mm = models.FloatField(null=True, blank=True, help_text="Rain since the previous report")
    smoke_ppm = models.FloatField(null=True, blank=True)
    temperature_c = models.FloatField(null=True, blank=True)
    battery_v = models.FloatField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["node", "-created_at"])]


class VibrationEvent(models.Model):
    MUDFLOW, EARTHQUAKE, VEHICLE, NOISE = "mudflow", "earthquake", "vehicle", "noise"
    CLASS_CHOICES = [
        (MUDFLOW, "Mudflow"),
        (EARTHQUAKE, "Earthquake"),
        (VEHICLE, "Vehicle"),
        (NOISE, "Noise"),
    ]

    node = models.ForeignKey(Node, related_name="events", on_delete=models.CASCADE)
    classification = models.CharField(max_length=12, choices=CLASS_CHOICES)
    confidence = models.FloatField()
    rms = models.FloatField()
    dominant_freq_hz = models.FloatField(null=True, blank=True)
    features = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["node", "classification", "-created_at"])]
