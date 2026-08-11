from rest_framework.permissions import BasePermission

from apps.sectors.policies import can_access_sector


class ProcessPermission(BasePermission):
    message = "Você não possui permissão para acessar processos neste setor."

    permission_by_action = {
        "list": "processes.view_administrativeprocess",
        "retrieve": "processes.view_administrativeprocess",
        "create": "processes.add_administrativeprocess",
        "partial_update": "processes.change_administrativeprocess",
        "update": "processes.change_administrativeprocess",
        "open": "processes.open_administrativeprocess",
        "forward": "processes.forward_administrativeprocess",
        "receive": "processes.receive_administrativeprocess",
        "return_action": "processes.return_administrativeprocess",
        "complete": "processes.complete_administrativeprocess",
        "reopen": "processes.reopen_administrativeprocess",
        "cancel": "processes.cancel_administrativeprocess",
        "archive": "processes.archive_administrativeprocess",
        "timeline": "processes.view_administrativeprocess",
    }

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        permission = self.permission_by_action.get(view.action)
        if permission is None:
            return True
        return request.user.has_perm(permission)

    def has_object_permission(self, request, view, obj):
        permission = self.permission_by_action.get(view.action)
        sector = obj.current_sector or obj.origin_sector
        return can_access_sector(
            request.user,
            permission=permission,
            sector=sector,
        )


class ProcessTypePermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm("processes.view_administrativeprocess")
