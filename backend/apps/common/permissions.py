from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsRescuerOrAdmin(BasePermission):
    """Rescuers (MChS) and admins only."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_rescuer", False))


class IsRescuerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_rescuer", False))
