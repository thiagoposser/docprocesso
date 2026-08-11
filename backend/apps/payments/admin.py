from django.contrib import admin

from .models import Payment, PaymentReceipt, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "masked_tax_id", "active", "updated_at")
    search_fields = ("name", "tax_id")
    list_filter = ("active",)

    @admin.display(description="CPF/CNPJ")
    def masked_tax_id(self, obj):
        return f"***{obj.tax_id[-4:]}" if obj.tax_id else ""


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("description", "supplier", "sector", "status", "due_date", "amount")
    list_filter = ("status", "sector", "due_date")
    search_fields = ("description", "supplier__name", "process__number")
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ("payment", "attachment", "created_by", "created_at")
    readonly_fields = ("payment", "attachment", "created_by", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
