from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.constants import DEFAULT_LANG, LANG_CHOICES

from .phone import normalize_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra):
        user = self.model(phone=normalize_phone(phone), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", User.ADMIN)
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    VILLAGER, BUYER, RESCUER, ADMIN = "villager", "buyer", "rescuer", "admin"
    ROLE_CHOICES = [
        (VILLAGER, "Villager"),
        (BUYER, "Buyer"),
        (RESCUER, "Rescuer / MChS"),
        (ADMIN, "Admin"),
    ]

    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default=VILLAGER)
    village = models.ForeignKey(
        "geo.Village", null=True, blank=True, on_delete=models.SET_NULL, related_name="residents"
    )
    language = models.CharField(max_length=2, choices=LANG_CHOICES, default=DEFAULT_LANG)
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    is_verified = models.BooleanField(default=False, help_text="Checked by the village (shows a tick)")
    home_lat = models.FloatField(null=True, blank=True)
    home_lon = models.FloatField(null=True, blank=True)
    home_label = models.CharField(max_length=60, blank=True, help_text="e.g. house number")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone"
    objects = UserManager()

    def __str__(self):
        return self.name or self.phone

    @property
    def is_rescuer(self):
        return self.role in (self.RESCUER, self.ADMIN)


class OTPCode(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class WatchedLocation(models.Model):
    """A place a user wants alerts about (pasture, road, relatives' village)."""

    user = models.ForeignKey(User, related_name="watched_locations", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    lat = models.FloatField()
    lon = models.FloatField()
    radius_km = models.FloatField(default=10.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.user})"
