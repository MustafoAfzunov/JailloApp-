"""Django settings for the Tabiyat Shield / JailoApp backend."""
import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "apps.common",
    "apps.accounts",
    "apps.geo",
    "apps.sensors",
    "apps.risk",
    "apps.alerts",
    "apps.reports",
    "apps.market",
    "apps.portal",
    "apps.telegrambot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "otp": "20/hour",
        "otp_verify": "60/hour",
        "report": "30/hour",
        "ingest": "1200/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Tabiyat Shield / JailoApp API",
    "DESCRIPTION": (
        "Natural-disaster early warning (mudflow, flood, avalanche, fire) and a village "
        "marketplace for Kyrgyzstan."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---- Project settings -------------------------------------------------------
NASA_FIRMS_MAP_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "")
NASA_FIRMS_SOURCE = os.getenv("NASA_FIRMS_SOURCE", "VIIRS_SNPP_NRT")
# Bounding box around Kyrgyzstan: west,south,east,north
FIRMS_BBOX = os.getenv("FIRMS_BBOX", "69.2,39.1,80.3,43.3")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "JailoAppBot")

TESTING = "test" in sys.argv

OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
# In DEBUG the OTP is printed to the console and returned in the response so the
# frontend can be developed without Telegram. Never enabled when DEBUG is off.
OTP_EXPOSE_IN_DEBUG = env_bool("OTP_EXPOSE_IN_DEBUG", True)

ALERT_RADIUS_KM = float(os.getenv("ALERT_RADIUS_KM", "15"))
FIRE_HOTSPOT_RADIUS_KM = float(os.getenv("FIRE_HOTSPOT_RADIUS_KM", "10"))
NODE_OFFLINE_AFTER_SECONDS = int(os.getenv("NODE_OFFLINE_AFTER_SECONDS", "300"))
NODE_STALE_AFTER_SECONDS = int(os.getenv("NODE_STALE_AFTER_SECONDS", "1800"))
WEATHER_CACHE_MINUTES = int(os.getenv("WEATHER_CACHE_MINUTES", "30"))
FIRMS_DAY_RANGE = int(os.getenv("FIRMS_DAY_RANGE", "2"))

OTP_RESEND_SECONDS = int(os.getenv("OTP_RESEND_SECONDS", "30"))

# Risk / alert tuning ---------------------------------------------------------
# Straight-line distance x PATH_FACTOR approximates the real length of a river channel.
PATH_FACTOR = float(os.getenv("PATH_FACTOR", "1.3"))
MUDFLOW_ASSUMED_SPEED_KMH = float(os.getenv("MUDFLOW_ASSUMED_SPEED_KMH", "20"))
SMOKE_ALERT_PPM = float(os.getenv("SMOKE_ALERT_PPM", "300"))
FIRE_TEMP_ALERT_C = float(os.getenv("FIRE_TEMP_ALERT_C", "60"))
ALERT_CLEAR_MINUTES = int(os.getenv("ALERT_CLEAR_MINUTES", "30"))
ALERT_DISMISS_COOLDOWN_MINUTES = int(os.getenv("ALERT_DISMISS_COOLDOWN_MINUTES", "30"))
# Send Telegram alerts from a background thread so ingest requests stay fast.
ALERT_ASYNC_DELIVERY = env_bool("ALERT_ASYNC_DELIVERY", not TESTING)
