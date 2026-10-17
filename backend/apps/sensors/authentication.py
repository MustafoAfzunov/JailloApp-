from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from .models import Node, hash_key


class DeviceUser:
    """Minimal user-like object so DRF treats an authenticated device as logged in."""

    is_authenticated = True
    is_anonymous = False
    is_rescuer = False

    def __init__(self, node):
        self.node = node
        self.pk = self.id = node.pk

    def __str__(self):
        return f"device:{self.node.device_id}"


class DeviceKeyAuthentication(BaseAuthentication):
    """Sensor nodes authenticate with the `X-Device-Key` header."""

    def authenticate(self, request):
        key = request.headers.get("X-Device-Key")
        if not key:
            return None
        node = (
            Node.objects.select_related("village")
            .filter(api_key_hash=hash_key(key.strip()), is_active=True)
            .first()
        )
        if node is None:
            raise AuthenticationFailed("Invalid device key.")
        return DeviceUser(node), node

    def authenticate_header(self, request):
        return "DeviceKey"


class IsDevice(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, DeviceUser)
