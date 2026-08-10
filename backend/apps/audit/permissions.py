from rest_framework.permissions import BasePermission


class CanViewAuditLog(BasePermission):
    message = "Permissão para visualizar auditoria é obrigatória."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.has_perm("audit.view_auditlog"))
