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
        "documents": "processes.view_administrativeprocess",
        "available_actions": "processes.view_administrativeprocess",
        "execute_transition": "processes.view_administrativeprocess",
        "eligible_assignees": "processes.assign_administrativeprocess",
        "assign": "processes.assign_administrativeprocess",
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


class WorkflowPermission(BasePermission):
    permissions = {"list": "processes.view_administrativeworkflow", "retrieve": "processes.view_administrativeworkflow", "create": "processes.add_administrativeworkflow", "partial_update": "processes.change_administrativeworkflow", "update": "processes.change_administrativeworkflow"}

    def has_permission(self, request, view):
        permission = self.permissions.get(view.action)
        return bool(request.user.is_authenticated and permission and request.user.has_perm(permission))


class WorkflowStagePermission(BasePermission):
    permissions = {"list": "processes.view_workflowstage", "retrieve": "processes.view_workflowstage", "create": "processes.add_workflowstage", "partial_update": "processes.change_workflowstage", "update": "processes.change_workflowstage"}

    def has_permission(self, request, view):
        permission = self.permissions.get(view.action)
        return bool(request.user.is_authenticated and permission and request.user.has_perm(permission))


class WorkflowTransitionPermission(BasePermission):
    permissions = {"list": "processes.view_workflowtransition", "retrieve": "processes.view_workflowtransition", "create": "processes.add_workflowtransition", "partial_update": "processes.change_workflowtransition", "update": "processes.change_workflowtransition"}

    def has_permission(self, request, view):
        permission = self.permissions.get(view.action)
        return bool(request.user.is_authenticated and permission and request.user.has_perm(permission))
