from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.mixins import AuditedWriteMixin

from .models import OrganizationalFunction, OrganizationalUnit, Sector, UserSectorMembership
from .permissions import OrganizationalFunctionPermission, OrganizationalUnitPermission, SectorPermission, UserSectorMembershipPermission
from .serializers import OrganizationalFunctionSerializer, OrganizationalUnitSerializer, SectorSerializer, UserSectorMembershipSerializer
from .services import build_sector_tree


def can_manage_sectors(user):
    return user.is_staff or user.has_perm("sectors.manage_sector")


def can_manage_units(user):
    return user.is_staff or user.has_perm("sectors.manage_organizational_unit")


class OrganizationalFunctionViewSet(
    AuditedWriteMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrganizationalFunctionSerializer
    permission_classes = [OrganizationalFunctionPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "code", "active", "created_at", "updated_at"]
    ordering = ["name", "id"]
    audit_label = "função organizacional"
    audit_fields = ("name", "code", "description", "active")

    def get_queryset(self):
        queryset = OrganizationalFunction.objects.all()
        params = self.request.query_params
        can_manage = self.request.user.is_staff or self.request.user.has_perm("sectors.manage_organizational_function")
        if not can_manage:
            return queryset.filter(active=True)
        if params.get("active") in {"true", "false"}:
            queryset = queryset.filter(active=params["active"] == "true")
        return queryset


class OrganizationalUnitViewSet(
    AuditedWriteMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrganizationalUnitSerializer
    permission_classes = [OrganizationalUnitPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "acronym", "description"]
    ordering_fields = ["name", "acronym", "active", "created_at", "updated_at"]
    ordering = ["name", "id"]
    audit_label = "unidade organizacional"
    audit_fields = ("name", "acronym", "description", "parent", "active")

    def get_queryset(self):
        queryset = OrganizationalUnit.objects.select_related("parent")
        params = self.request.query_params
        if not can_manage_units(self.request.user):
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
                raise ValidationError({"parent": "Informe um ID de unidade ou 'root'."}) from error
        return queryset


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
    search_fields = ["name", "code", "unit__name", "unit__acronym", "manager__username", "manager__first_name", "manager__last_name"]
    ordering_fields = ["name", "code", "active", "created_at", "updated_at"]
    ordering = ["name", "id"]
    audit_label = "setor"
    audit_fields = ("unit", "name", "code", "parent", "manager", "active")

    def get_queryset(self):
        queryset = Sector.objects.select_related("unit", "parent", "manager")
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
        unit = params.get("unit")
        if unit:
            try:
                queryset = queryset.filter(unit_id=int(unit))
            except ValueError as error:
                raise ValidationError({"unit": "Informe um ID de unidade válido."}) from error
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
