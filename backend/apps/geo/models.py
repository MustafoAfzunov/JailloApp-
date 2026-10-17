from django.db import models
from django.utils.text import slugify


class Village(models.Model):
    slug = models.SlugField(unique=True, blank=True)
    name = models.CharField(max_length=120, help_text="Default (Russian) name")
    name_ky = models.CharField(max_length=120, blank=True)
    name_en = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    population = models.PositiveIntegerField(null=True, blank=True)
    valley = models.CharField(max_length=120, blank=True, help_text="Valley name in Russian")
    valley_ky = models.CharField(max_length=120, blank=True)
    elevation_m = models.PositiveIntegerField(null=True, blank=True)
    river_name = models.CharField(max_length=120, blank=True)
    river_name_ky = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def name_for(self, lang):
        return {"ky": self.name_ky, "en": self.name_en}.get(lang) or self.name

    def valley_for(self, lang):
        return (self.valley_ky if lang == "ky" else self.valley) or self.valley

    def river_for(self, lang):
        return (self.river_name_ky if lang == "ky" else self.river_name) or self.river_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name_en or self.name) or "village"
            slug, i = base, 2
            while Village.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, i = f"{base}-{i}", i + 1
            self.slug = slug
        super().save(*args, **kwargs)


class EvacuationPoint(models.Model):
    village = models.ForeignKey(Village, related_name="evacuation_points", on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    lat = models.FloatField()
    lon = models.FloatField()
    notes = models.CharField(max_length=255, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    name_ky = models.CharField(max_length=160, blank=True)
    notes_ky = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False, help_text="Main shelter shown first")
    has_clinic = models.BooleanField(default=False)
    has_water = models.BooleanField(default=False)

    class Meta:
        ordering = ["village", "-is_primary", "name"]

    def name_for(self, lang):
        return (self.name_ky if lang == "ky" else self.name) or self.name

    def notes_for(self, lang):
        return (self.notes_ky if lang == "ky" else self.notes) or self.notes

    def __str__(self):
        return f"{self.name} ({self.village})"


def _pick(obj, base, lang):
    """Return obj.<base>_ky for Kyrgyz (falling back to Russian), otherwise obj.<base>."""
    ru = getattr(obj, base)
    return (getattr(obj, f"{base}_ky") or ru) if lang == "ky" else ru


class HazardZone(models.Model):
    """A polygon on the village map: a danger strip (mudflow ravine) or a safe area (high ground)."""

    DANGER, SAFE = "danger", "safe"
    village = models.ForeignKey(Village, related_name="zones", on_delete=models.CASCADE)
    kind = models.CharField(max_length=6, choices=[(DANGER, "Danger"), (SAFE, "Safe")])
    hazard = models.CharField(max_length=10, blank=True, help_text="mudflow / flood / avalanche / fire")
    name = models.CharField(max_length=160)
    name_ky = models.CharField(max_length=160, blank=True)
    polygon = models.JSONField(help_text="[[lat, lon], ...]")

    def __str__(self):
        return f"{self.name} ({self.kind})"

    def name_for(self, lang):
        return _pick(self, "name", lang)


class EvacuationRoute(models.Model):
    """Walking route from the village to a shelter, as a polyline."""

    village = models.ForeignKey(Village, related_name="routes", on_delete=models.CASCADE)
    point = models.ForeignKey(EvacuationPoint, related_name="routes", on_delete=models.CASCADE)
    path = models.JSONField(help_text="[[lat, lon], ...] from the village towards the shelter")


class Building(models.Model):
    """Houses drawn on the village map. The user's own house is matched by label."""

    village = models.ForeignKey(Village, related_name="buildings", on_delete=models.CASCADE)
    label = models.CharField(max_length=60, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()


class Announcement(models.Model):
    village = models.ForeignKey(Village, related_name="announcements", on_delete=models.CASCADE)
    source = models.CharField(max_length=120, help_text="Who posted it, e.g. Village head and vet")
    source_ky = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=200)
    title_ky = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    body_ky = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class VillageContact(models.Model):
    HEAD, AMBULANCE, EMERGENCY, VET, MEDIC, PASTURE, TRANSPORT, SUPPORT = (
        "head", "ambulance", "emergency", "vet", "medic", "pasture", "transport", "support",
    )
    ROLE_CHOICES = [(r, r.title()) for r in (HEAD, AMBULANCE, EMERGENCY, VET, MEDIC, PASTURE, TRANSPORT, SUPPORT)]

    village = models.ForeignKey(Village, related_name="contacts", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    name = models.CharField(max_length=120, blank=True)
    name_ky = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40)
    phone_display = models.CharField(max_length=60, blank=True, help_text="How to print the number")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class RoadStatus(models.Model):
    OPEN, LIMITED, CLOSED = "open", "limited", "closed"
    village = models.ForeignKey(Village, related_name="roads", on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    name_ky = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=8, choices=[(OPEN, "Open"), (LIMITED, "Limited"), (CLOSED, "Closed")], default=OPEN)
    note = models.CharField(max_length=255, blank=True)
    note_ky = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "road statuses"
