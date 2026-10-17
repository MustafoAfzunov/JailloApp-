"""Alert lifecycle: create / escalate / resolve alerts and notify people.

Rules
- Medium and above creates an alert (shows in the feed). High and above notifies people.
- Critical also switches on the village siren.
- Engine alerts clear themselves after ALERT_CLEAR_MINUTES below medium; manual, report and
  demo alerts stay until a rescuer resolves them.
- A dismissed alert (false alarm) is not re-opened for ALERT_DISMISS_COOLDOWN_MINUTES unless
  the engine reaches critical.
"""
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from apps.accounts.models import User, WatchedLocation
from apps.common import telegram
from apps.common.constants import LEVEL_CRITICAL, LEVEL_HIGH, LEVEL_MEDIUM, LEVEL_RANK
from apps.common.geo import bbox, haversine_km
from apps.common.messages import build_alert_texts

from .models import Alert, AlertDelivery, SirenCommand

log = logging.getLogger(__name__)

RANK_MEDIUM = LEVEL_RANK[LEVEL_MEDIUM]
RANK_HIGH = LEVEL_RANK[LEVEL_HIGH]
RANK_CRITICAL = LEVEL_RANK[LEVEL_CRITICAL]


def _build_texts(village, hazard, level, eta_seconds, simulated):
    point = village.evacuation_points.first()
    return build_alert_texts(hazard, level, village, eta_seconds, point, simulated)


@transaction.atomic
def upsert_alert(village, hazard, level, *, source, eta_seconds=None, details=None,
                 simulated=False, created_by=None, allow_downgrade=True, now=None):
    """Create the active alert for (village, hazard) or update the existing one."""
    now = now or timezone.now()
    alert = Alert.objects.select_for_update().filter(village=village, hazard=hazard, status=Alert.ACTIVE).first()
    if alert is None:
        alert = Alert(
            village=village, hazard=hazard, source=source, is_simulated=simulated, created_by=created_by
        )
    elif not allow_downgrade and LEVEL_RANK[level] < LEVEL_RANK[alert.level]:
        level = alert.level

    alert.level = level
    alert.last_elevated_at = now
    if details is not None:
        alert.details = details
    if eta_seconds is not None:
        alert.eta_at = now + timedelta(seconds=eta_seconds)
    remaining = None if alert.eta_at is None else max(0, int((alert.eta_at - now).total_seconds()))
    alert.texts = _build_texts(village, hazard, level, remaining, alert.is_simulated)
    alert.save()
    return alert


def resolve_alert(alert, status=Alert.RESOLVED, by=None, now=None):
    now = now or timezone.now()
    alert.status = status
    alert.resolved_at = now
    alert.resolved_by = by
    alert.save(update_fields=["status", "resolved_at", "resolved_by", "updated_at"])
    if alert.siren_commands.filter(action=SirenCommand.ON).exists():
        SirenCommand.objects.create(village=alert.village, alert=alert, action=SirenCommand.OFF)
    return alert


def trigger_siren(alert):
    SirenCommand.objects.get_or_create(
        alert=alert, action=SirenCommand.ON, defaults={"village": alert.village}
    )


# ---------------------------------------------------------------- notifications
def recipients_for(alert):
    village = alert.village
    users = {u.pk: u for u in User.objects.filter(is_active=True, village=village)}
    lat_min, lat_max, lon_min, lon_max = bbox(village.lat, village.lon, 100)
    watchers = WatchedLocation.objects.select_related("user").filter(
        user__is_active=True, lat__range=(lat_min, lat_max), lon__range=(lon_min, lon_max)
    )
    for w in watchers:
        if haversine_km(w.lat, w.lon, village.lat, village.lon) <= w.radius_km:
            users[w.user_id] = w.user
    for u in User.objects.filter(is_active=True, role__in=(User.RESCUER, User.ADMIN)):
        users[u.pk] = u
    return list(users.values())


def deliver_alert(alert_id):
    """Send the alert to everyone concerned (once per user and level)."""
    alert = Alert.objects.select_related("village").get(pk=alert_id)
    sent = 0
    for user in recipients_for(alert):
        delivery, created = AlertDelivery.objects.get_or_create(
            alert=alert,
            user=user,
            level=alert.level,
            defaults={"channel": "telegram" if user.telegram_chat_id else "none"},
        )
        if not created:
            continue
        if not user.telegram_chat_id:
            delivery.status = "no_channel"
            delivery.save(update_fields=["status"])
            continue
        t = alert.texts.get(user.language) or alert.texts.get("ru") or {}
        ok, error = telegram.safe_send(user.telegram_chat_id, f"{t.get('title', '')}\n{t.get('body', '')}")
        delivery.status = "sent" if ok else "failed"
        delivery.error = error
        delivery.save(update_fields=["status", "error"])
        sent += ok
    return sent


def _dispatch(alert_id):
    if not settings.ALERT_ASYNC_DELIVERY:
        deliver_alert(alert_id)
        return

    def run():
        try:
            deliver_alert(alert_id)
        except Exception:
            log.exception("alert delivery failed")
        finally:
            close_old_connections()

    threading.Thread(target=run, daemon=True).start()


def maybe_notify(alert):
    """Notify when the level has risen above what people were already told."""
    rank = LEVEL_RANK[alert.level]
    if rank < RANK_HIGH or rank <= alert.notified_rank:
        return False
    alert.notified_rank = rank
    alert.save(update_fields=["notified_rank"])
    if rank >= RANK_CRITICAL:
        trigger_siren(alert)
    _dispatch(alert.pk)
    return True


# ---------------------------------------------------------------- entry points
def sync_from_results(village, results, now=None):
    """Called by the risk engine after each evaluation."""
    now = now or timezone.now()
    for r in results:
        rank = LEVEL_RANK[r.level]
        active = Alert.objects.filter(village=village, hazard=r.hazard, status=Alert.ACTIVE).first()
        if rank >= RANK_MEDIUM:
            if active is None and rank < RANK_CRITICAL:
                cooldown = now - timedelta(minutes=settings.ALERT_DISMISS_COOLDOWN_MINUTES)
                if Alert.objects.filter(
                    village=village, hazard=r.hazard, status=Alert.DISMISSED, resolved_at__gte=cooldown
                ).exists():
                    continue
            engine_owned = active is None or active.source == Alert.SOURCE_ENGINE
            alert = upsert_alert(
                village, r.hazard, r.level, source=Alert.SOURCE_ENGINE, eta_seconds=r.eta_seconds,
                details=r.details, allow_downgrade=engine_owned, now=now,
            )
            maybe_notify(alert)
        elif active and active.source == Alert.SOURCE_ENGINE:
            if now - active.last_elevated_at >= timedelta(minutes=settings.ALERT_CLEAR_MINUTES):
                resolve_alert(active, Alert.RESOLVED, now=now)


def raise_manual_alert(village, hazard, level, *, user=None, source=Alert.SOURCE_MANUAL,
                       eta_seconds=None, simulated=False, details=None):
    """Alert created by a rescuer, a confirmed citizen report or the demo trigger."""
    alert = upsert_alert(
        village, hazard, level, source=source, eta_seconds=eta_seconds, details=details or {},
        simulated=simulated, created_by=user, allow_downgrade=False,
    )
    maybe_notify(alert)
    return alert
