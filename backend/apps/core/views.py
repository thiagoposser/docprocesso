from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from apps.users.permissions import IsAdministrator
from .models import SystemSettings
from .serializers import AdminSettingsSerializer, PublicSettingsSerializer
from apps.audit.models import AuditAction
from apps.audit.services import record_audit, snapshot
from apps.notifications.models import NotificationLevel, NotificationType
from apps.notifications.services import NotificationService
from .services import dashboard_summary


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Small endpoint used by Docker and infrastructure monitoring."""
    return Response({"status": "ok", "service": "django"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    return Response(dashboard_summary(request.user))


class PublicSettingsView(RetrieveUpdateAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicSettingsSerializer
    http_method_names = ["get", "head", "options"]

    def get_object(self):
        return SystemSettings.load()


class AdminSettingsView(RetrieveUpdateAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AdminSettingsSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return SystemSettings.load()

    def perform_update(self, serializer):
        instance = serializer.instance
        fields = ("system_name", "system_short_name", "system_description", "version", "primary_color", "timezone", "language_code", "support_email", "support_url", "maintenance_mode")
        old_values = snapshot(instance, fields)
        updated = serializer.save()
        record_audit(action=AuditAction.SETTINGS_CHANGED, description="Configurações do sistema alteradas", request=self.request, entity=updated, old_values=old_values, new_values=snapshot(updated, fields))
        NotificationService.create_for_group("Administrador", exclude_user=self.request.user, title="Configurações atualizadas", message="As configurações gerais do sistema foram alteradas.", type=NotificationType.ADMIN, level=NotificationLevel.INFO, action_url="/configuracoes")
