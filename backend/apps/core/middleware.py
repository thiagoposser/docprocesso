from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from .models import SystemSettings


class MaintenanceModeMiddleware:
    """Blocks non-admin application traffic while keeping auth and monitoring available."""

    exempt_prefixes = ("/api/health/", "/api/settings/public/", "/api/auth/login/", "/api/auth/refresh/", "/api/auth/logout/", "/admin/", "/media/", "/static/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not any(request.path.startswith(prefix) for prefix in self.exempt_prefixes):
            settings = SystemSettings.load()
            if settings.maintenance_mode and not self._is_administrator(request):
                return JsonResponse({"detail": "Sistema em manutenção.", "code": "maintenance_mode"}, status=503)
        return self.get_response(request)

    @staticmethod
    def _is_administrator(request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and (user.is_staff or user.groups.filter(name="Administrador").exists()):
            return True
        try:
            authenticated = JWTAuthentication().authenticate(request)
        except (AuthenticationFailed, InvalidToken):
            return False
        if not authenticated:
            return False
        user, _ = authenticated
        return user.is_staff or user.groups.filter(name="Administrador").exists()
