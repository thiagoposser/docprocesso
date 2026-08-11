from rest_framework.permissions import SAFE_METHODS, BasePermission


class SectorPermission(BasePermission):
    message = "Você não possui permissão para gerenciar setores."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.has_perm("sectors.manage_sector")


class UserSectorMembershipPermission(BasePermission):
    message = "Você não possui permissão para gerenciar vínculos de setores."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return user.is_staff or user.groups.filter(name="Administrador").exists() or user.has_perm("sectors.manage_user_sector_membership")
