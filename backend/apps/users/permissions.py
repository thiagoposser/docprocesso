from rest_framework.permissions import BasePermission


class IsAdministrator(BasePermission):
    """Authorization is enforced server-side through Django groups/staff status."""

    message = "Administrator permission is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user.is_authenticated and (user.is_staff or user.groups.filter(name="Administrador").exists()))
