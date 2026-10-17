from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.constants import HAZARD_CHOICES, LEVEL_CHOICES


class Alert(models.Model):
    ACTIVE, RESOLVED, DISMISSED = "active", "resolved", "dismissed"
    STATUS_CHOICES = [(ACTIVE, "Active"), (RESOLVED, "Resolved"), (DISMISSED, "Dismissed (false alarm)")]
    SOURCE_ENGINE, SOURCE_MANUAL, SOURCE_REPORT, SOURCE_SIM = "engine", "manual", "report", "simulated"
    SOURCE_CHOICES = [
        (SOURCE_ENGINE, "Risk engine"),
        (SOURCE_MANUAL, "Rescuer"),
        (SOURCE_REPORT, "Citizen report"),
        (SOURCE_SIM, "Demo / simulation"),
    ]

    village = models.ForeignKey("geo.Village", related_name="alerts", on_delete=models.CASCADE)
    hazard = models.CharField(max_length=12, choices=HAZARD_CHOICES)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE, db_index=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_ENGINE)
    is_simulated = models.BooleanField(default=False)
    texts = models.JSONField(default=dict, blank=True, help_text='{"ru": {"title":..., "body":...}, ...}')
    details = models.JSONField(default=dict, blank=True)
    eta_at = models.DateTimeField(null=True, blank=True)
    notified_rank = models.SmallIntegerField(default=-1)
    last_elevated_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts_created"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts_resolved"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["village", "hazard"], condition=Q(status="active"), name="uniq_active_alert"
            )
        ]

    def __str__(self):
        return f"{self.hazard}/{self.level} @ {self.village} [{self.status}]"


class AlertDelivery(models.Model):
    """Log of who was notified, so nobody gets the same alert level twice."""

    alert = models.ForeignKey(Alert, related_name="deliveries", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="alert_deliveries", on_delete=models.CASCADE)
    level = models.CharField(max_length=10)
    channel = models.CharField(max_length=10, default="telegram")
    status = models.CharField(max_length=12, default="pending")  # pending / sent / failed / no_channel
    error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["alert", "user", "level"], name="uniq_alert_delivery")]


class SafeCheckin(models.Model):
    """The 'I'm safe' button."""

    alert = models.ForeignKey(Alert, related_name="checkins", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="checkins", on_delete=models.CASCADE)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["alert", "user"], name="uniq_checkin")]


class SirenCommand(models.Model):
    """Polled by the village LoRa gateway node to switch the siren on or off."""

    ON, OFF = "on", "off"
    village = models.ForeignKey("geo.Village", related_name="siren_commands", on_delete=models.CASCADE)
    alert = models.ForeignKey(Alert, related_name="siren_commands", on_delete=models.CASCADE)
    action = models.CharField(max_length=3, choices=[(ON, "On"), (OFF, "Off")])
    created_at = models.DateTimeField(auto_now_add=True)
    acked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
