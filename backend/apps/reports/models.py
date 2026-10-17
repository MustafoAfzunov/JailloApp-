from django.conf import settings
from django.db import models
from django.utils import timezone


class HazardReport(models.Model):
    SMOKE, RISING_WATER, CRACKS, AVALANCHE, MUDFLOW, FIRE, ROCKFALL, OTHER = (
        "smoke", "rising_water", "cracks", "avalanche", "mudflow", "fire", "rockfall", "other",
    )
    TYPE_CHOICES = [
        (SMOKE, "Smoke"),
        (RISING_WATER, "Rising water"),
        (CRACKS, "Cracks / landslide"),
        (AVALANCHE, "Avalanche"),
        (MUDFLOW, "Mudflow"),
        (FIRE, "Fire"),
        (ROCKFALL, "Rockfall / road blocked"),
        (OTHER, "Other"),
    ]
    # what each report type means for the alert system
    HAZARD_FOR_TYPE = {
        SMOKE: "fire", FIRE: "fire", RISING_WATER: "flood",
        CRACKS: "mudflow", MUDFLOW: "mudflow", AVALANCHE: "avalanche",
    }

    PENDING, CONFIRMED, DISMISSED = "pending", "confirmed", "dismissed"
    STATUS_CHOICES = [(PENDING, "Pending"), (CONFIRMED, "Confirmed"), (DISMISSED, "Dismissed")]
    SOURCE_CHOICES = [("app", "App"), ("telegram", "Telegram bot")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reports", on_delete=models.CASCADE)
    village = models.ForeignKey("geo.Village", null=True, blank=True, related_name="reports", on_delete=models.SET_NULL)
    type = models.CharField(max_length=14, choices=TYPE_CHOICES)
    description = models.TextField(blank=True, max_length=1000)
    photo = models.ImageField(upload_to="reports/", null=True, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="app")
    crowd_confirmed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="reports_reviewed", on_delete=models.SET_NULL
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} @ {self.lat:.3f},{self.lon:.3f} [{self.status}]"

    @property
    def hazard(self):
        return self.HAZARD_FOR_TYPE.get(self.type)
