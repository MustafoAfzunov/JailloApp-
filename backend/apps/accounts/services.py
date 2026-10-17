"""Phone OTP login. Codes are delivered through the Telegram bot (see telegrambot app)."""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from apps.common import telegram

from .models import OTPCode, User

log = logging.getLogger(__name__)


def _hash(phone, code):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{phone}:{code}".encode()).hexdigest()


def get_or_create_user(phone, **defaults):
    """Return (user, created). Uses create_user so the password is unusable."""
    user = User.objects.filter(phone=phone).first()
    if user:
        return user, False
    return User.objects.create_user(phone, **defaults), True


def dev_echo_enabled():
    return settings.DEBUG and settings.OTP_EXPOSE_IN_DEBUG


def request_otp(phone):
    """Create and deliver a code. Returns {'channel': 'telegram'|'dev'|'none', ...}."""
    now = timezone.now()
    last = OTPCode.objects.filter(phone=phone).first()
    if last:
        wait = settings.OTP_RESEND_SECONDS - (now - last.created_at).total_seconds()
        if wait > 0:
            raise Throttled(wait=int(wait) + 1)

    code = f"{secrets.randbelow(10**6):06d}"
    OTPCode.objects.create(
        phone=phone,
        code_hash=_hash(phone, code),
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )

    text = f"Jailo: код входа / login code: {code}\nНикому не сообщайте. Do not share it."
    user = User.objects.filter(phone=phone).first()
    if user and user.telegram_chat_id:
        ok, _ = telegram.safe_send(user.telegram_chat_id, text)
        if ok:
            return {"channel": "telegram"}

    if dev_echo_enabled():
        print(f"[OTP dev] {phone}: {code}")  # noqa: T201 - console only, DEBUG only
        return {"channel": "dev", "dev_code": code}

    return {"channel": "none"}


def verify_otp(phone, code, name=""):
    """Validate a code; return (user, created). Raises ValidationError on failure."""
    now = timezone.now()
    otp = OTPCode.objects.filter(phone=phone, used=False, expires_at__gt=now).first()
    if otp is None:
        raise ValidationError({"code": "Code expired or not requested."})
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise ValidationError({"code": "Too many attempts. Request a new code."})

    otp.attempts += 1
    if not hmac.compare_digest(otp.code_hash, _hash(phone, str(code).strip())):
        otp.save(update_fields=["attempts"])
        raise ValidationError({"code": "Wrong code."})

    otp.used = True
    otp.save(update_fields=["attempts", "used"])

    user, created = get_or_create_user(phone, name=(name or "").strip()[:120])
    if not created and name and not user.name:
        user.name = name.strip()[:120]
        user.save(update_fields=["name"])
    return user, created
