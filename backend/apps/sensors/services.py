from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .classifier import classify, features_from_samples
from .models import Reading, VibrationEvent


def _is_fire_signal(smoke, temp):
    return (smoke is not None and smoke >= settings.SMOKE_ALERT_PPM * 0.5) or (
        temp is not None and temp >= settings.FIRE_TEMP_ALERT_C * 0.8
    )


def ingest(node, data):
    """Store one reading from a node, classify vibration and refresh risk if relevant."""
    now = timezone.now()
    rms, freq = data.get("vibration_rms"), data.get("dominant_freq_hz")
    samples = data.get("samples")
    if samples:
        rms, freq = features_from_samples(samples, data.get("sample_rate_hz") or 200)

    extra = {}
    for key in ("crackle_score", "edge_class", "edge_confidence", "humidity"):
        if data.get(key) is not None:
            extra[key] = data[key]

    reading = Reading.objects.create(
        node=node,
        created_at=now,
        vibration_rms=rms,
        dominant_freq_hz=freq,
        water_level_cm=data.get("water_level_cm"),
        rain_mm=data.get("rain_mm"),
        smoke_ppm=data.get("smoke_ppm"),
        temperature_c=data.get("temperature_c"),
        battery_v=data.get("battery_v"),
        extra=extra,
    )

    node.last_seen = now
    fields = ["last_seen"]
    if data.get("battery_v") is not None:
        node.battery_v = data["battery_v"]
        fields.append("battery_v")
    node.save(update_fields=fields)

    event = None
    if rms is not None:
        prev = list(
            Reading.objects.filter(
                node=node,
                created_at__gte=now - timedelta(seconds=120),
                vibration_rms__isnull=False,
            )
            .exclude(pk=reading.pk)
            .values_list("vibration_rms", flat=True)
        )
        c = classify(rms, freq, prev, data.get("edge_class"), data.get("edge_confidence"))
        if c.label != "noise":
            event = VibrationEvent.objects.create(
                node=node,
                classification=c.label,
                confidence=c.confidence,
                rms=rms,
                dominant_freq_hz=freq,
                features={"sustained": c.sustained, "rising": c.rising},
                created_at=now,
            )

    urgent = (event is not None and event.classification in ("mudflow", "earthquake")) or _is_fire_signal(
        data.get("smoke_ppm"), data.get("temperature_c")
    )
    # Otherwise refresh the village risk at most once a minute.
    if urgent or cache.add(f"risk-eval:{node.village_id}", 1, 60):
        from apps.risk.engine import evaluate_village

        evaluate_village(node.village)

    return reading, event
