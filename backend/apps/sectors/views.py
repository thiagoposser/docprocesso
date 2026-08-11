from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.mixins import AuditedWriteMixin

from .models import Sector, UserSectorMembership
from .permissions import SectorPermission, UserSectorMembershipPermission
from .serializers import SectorSerializer, UserSectorMembershipSerializer
from .services import build_sector_tree


def can_manage_sectors(user):
    return user.is_staff or user.has_perm("sectors.manage_sector")


class SectorViewSet(
    AuditedWriteMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SectorSerializer
    permission_classes = [SectorPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "manager__username", "manager__first_name", "manager__last_name"]
    ordering_fields = ["name", "code", "active", "created_at", "updated_at"]
    ordering = ["name", "id"]
    audit_label = "setor"
    audit_fields = ("name", "code", "parent", "manager", "active")

    def get_queryset(self):
        queryset = Sector.objects.select_related("parent", "manager")
        params = self.request.query_params
        if not can_manage_sectors(self.request.user):
            queryset = queryset.filter(active=True)
        elif params.get("active") in {"true", "false"}:
            queryset = queryset.filter(active=params["active"] == "true")

        parent = params.get("parent")
        if parent == "root":
            queryset = queryset.filter(parent__isnull=True)
        elif parent:
            try:
                queryset = queryset.filter(parent_id=int(parent))
            except ValueError as error:
                raise ValidationError({"parent": "Informe um ID de setor ou 'root'."}) from error
        return queryset

    @action(detail=False, methods=["get"])
    def tree(self, request):
        sectors = self.filter_queryset(self.get_queryset())
        return Response(build_sector_tree(sectors))


class UserSectorMembershipViewSet(
    AuditedWriteMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserSectorMembershipSerializer
    permission_classes = [UserSectorMembershipPermission]
    audit_label = "vínculo de usuário com setor"
    audit_fields = ("user", "sector", "active", "is_primary", "is_manager")

    def get_queryset(self):
        queryset = UserSectorMembership.objects.select_related("user", "sector")
        user = self.request.user
        can_manage = user.is_staff or user.groups.filter(name="Administrador").exists() or user.has_perm("sectors.manage_user_sector_membership")
        if not can_manage:
            return queryset.filter(user=user, active=True)
        params = self.request.query_params
        if params.get("user"):
            queryset = queryset.filter(user_id=params["user"])
        if params.get("sector"):
            queryset = queryset.filter(sector_id=params["sector"])
        if params.get("active") in {"true", "false"}:
            queryset = queryset.filter(active=params["active"] == "true")
        return queryset
