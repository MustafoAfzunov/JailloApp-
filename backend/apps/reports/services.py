from datetime import timedelta

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.alerts import services as alert_services
from apps.alerts.models import Alert
from apps.common.constants import LEVEL_HIGH
from apps.common.geo import bbox, haversine_km
from apps.common.notify import notify_user
from apps.geo.services import nearest_village

from .models import HazardReport

CROWD_RADIUS_KM = 3.0
CROWD_WINDOW = timedelta(minutes=60)
CROWD_MIN_REPORTERS = 3


def _maps_link(lat, lon):
    return f"https://maps.google.com/?q={lat},{lon}"


def after_create(report):
    """Assign a village, tell rescuers, and check for crowd confirmation."""
    if report.village_id is None:
        village = nearest_village(report.lat, report.lon)
        if village:
            report.village = village
            report.save(update_fields=["village"])

    where = report.village.name if report.village_id else "?"
    text = (
        f"📢 New hazard report: {report.get_type_display()} near {where}\n"
        f"{_maps_link(report.lat, report.lon)}"
    )
    for rescuer in User.objects.filter(is_active=True, role__in=(User.RESCUER, User.ADMIN)):
        notify_user(rescuer, text)

    _check_crowd(report)


def _check_crowd(report):
    """3+ different people reporting the same thing nearby within an hour = high-risk alert."""
    lat_min, lat_max, lon_min, lon_max = bbox(report.lat, report.lon, CROWD_RADIUS_KM)
    similar = HazardReport.objects.filter(
        type=report.type,
        created_at__gte=timezone.now() - CROWD_WINDOW,
        lat__range=(lat_min, lat_max),
        lon__range=(lon_min, lon_max),
    ).exclude(status=HazardReport.DISMISSED)
    similar = [r for r in similar if haversine_km(r.lat, r.lon, report.lat, report.lon) <= CROWD_RADIUS_KM]
    if len({r.user_id for r in similar}) >= CROWD_MIN_REPORTERS:
        for r in similar:
            if not r.crowd_confirmed:
                r.crowd_confirmed = True
                r.save(update_fields=["crowd_confirmed"])
        _raise_alert(report, user=None)


def _raise_alert(report, user):
    hazard = report.hazard
    if hazard and report.village_id:
        return alert_services.raise_manual_alert(
            report.village, hazard, LEVEL_HIGH, user=user, source=Alert.SOURCE_REPORT,
            details={"report_id": report.pk, "crowd_confirmed": report.crowd_confirmed},
        )
    return None


def create_report(user, type, lat, lon, description="", photo_bytes=None, source="app"):
    report = HazardReport(user=user, type=type, lat=lat, lon=lon, description=description, source=source)
    if photo_bytes:
        report.photo.save(f"tg-{timezone.now():%Y%m%d%H%M%S}.jpg", ContentFile(photo_bytes), save=False)
    report.save()
    after_create(report)
    return report


def review(report, reviewer, status):
    report.status = status
    report.reviewed_by = reviewer
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    alert = None
    if status == HazardReport.CONFIRMED:
        alert = _raise_alert(report, user=reviewer)
        notify_user(report.user, "✅ Your hazard report was confirmed by rescuers. Thank you!")
    return alert
