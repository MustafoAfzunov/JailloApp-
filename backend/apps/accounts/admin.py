from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User, WatchedLocation


class CreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("phone", "name", "role")


class ChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = ChangeForm
    add_form = CreationForm
    ordering = ("phone",)
    list_display = ("phone", "name", "role", "village", "telegram_chat_id", "is_active")
    list_filter = ("role", "is_active", "village")
    search_fields = ("phone", "name")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profile", {"fields": ("name", "role", "village", "language", "telegram_chat_id")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "name", "role", "password1", "password2")}),
    )


@admin.register(WatchedLocation)
class WatchedLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "lat", "lon", "radius_km")
