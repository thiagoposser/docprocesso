from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.sectors.policies import can_access_sector


class SupplierPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        permission = "payments.view_supplier" if request.method in SAFE_METHODS else (
            "payments.add_supplier" if view.action == "create" else "payments.change_supplier"
        )
        return request.user.has_perm(permission)


class PaymentPermission(BasePermission):
    message = "Você não possui permissão para acessar dados financeiros neste setor."

    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.has_perm("payments.view_financial_data") or not request.user.has_perm("processes.view_administrativeprocess"):
            return False
        permission = {
            "create": "payments.add_payment", "schedule": "payments.schedule_payment",
            "confirm": "payments.confirm_payment", "cancel": "payments.cancel_payment",
            "receipts": "payments.manage_payment_receipt" if request.method == "POST" else "payments.view_payment",
        }.get(view.action, "payments.view_payment" if request.method in SAFE_METHODS else "payments.change_payment")
        return request.user.has_perm(permission)

    def has_object_permission(self, request, view, obj):
        permission = {
            "schedule": "payments.schedule_payment", "confirm": "payments.confirm_payment",
            "cancel": "payments.cancel_payment",
            "receipts": "payments.manage_payment_receipt" if request.method == "POST" else "payments.view_payment",
        }.get(view.action, "payments.view_payment" if request.method in SAFE_METHODS else "payments.change_payment")
        return can_access_sector(request.user, permission=permission, sector=obj.sector)
