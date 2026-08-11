import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def normalize_tax_id(value):
    return re.sub(r"\D", "", value or "")


def validate_tax_id(value):
    normalized = normalize_tax_id(value)
    if len(normalized) not in {11, 14}:
        raise ValidationError("Informe um CPF ou CNPJ com 11 ou 14 dígitos.")


class Supplier(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    tax_id = models.CharField(max_length=14, unique=True, validators=[validate_tax_id])
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=30, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        default_permissions = ("add", "change", "view")
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(bank_name="", bank_branch="", bank_account="") | (~models.Q(bank_name="") & ~models.Q(bank_branch="") & ~models.Q(bank_account=""))),
                name="supplier_bank_data_complete",
            ),
        ]
        verbose_name = "fornecedor"
        verbose_name_plural = "fornecedores"

    def clean(self):
        super().clean()
        self.tax_id = normalize_tax_id(self.tax_id)
        validate_tax_id(self.tax_id)
        bank_values = (self.bank_name, self.bank_branch, self.bank_account)
        if any(bank_values) and not all(bank_values):
            raise ValidationError({"bank_account": "Informe banco, agência e conta em conjunto."})

    def save(self, *args, **kwargs):
        self.tax_id = normalize_tax_id(self.tax_id)
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    SCHEDULED = "SCHEDULED", "Agendado"
    PAID = "PAID", "Pago"
    CANCELLED = "CANCELLED", "Cancelado"


class Payment(models.Model):
    process = models.ForeignKey("processes.AdministrativeProcess", on_delete=models.PROTECT, related_name="payments")
    document = models.ForeignKey("documents.Document", on_delete=models.PROTECT, related_name="payments", blank=True, null=True)
    sector = models.ForeignKey("sectors.Sector", on_delete=models.PROTECT, related_name="payments")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="payments")
    description = models.CharField(max_length=250)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    due_date = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="confirmed_payments", blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_payments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "id"]
        default_permissions = ("add", "change", "view")
        permissions = [
            ("view_financial_data", "Pode visualizar dados financeiros"),
            ("confirm_payment", "Pode confirmar pagamentos"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_amount_nonnegative"),
            models.CheckConstraint(condition=models.Q(paid_amount__isnull=True) | models.Q(paid_amount__gte=0), name="payment_paid_amount_nonnegative"),
            models.CheckConstraint(
                condition=~models.Q(status=PaymentStatus.PAID) | models.Q(paid_at__isnull=False, paid_amount__isnull=False, paid_by__isnull=False),
                name="payment_paid_fields_required",
            ),
            models.CheckConstraint(
                condition=~models.Q(status=PaymentStatus.SCHEDULED) | models.Q(scheduled_at__isnull=False),
                name="payment_scheduled_at_required",
            ),
            models.CheckConstraint(
                condition=~models.Q(status=PaymentStatus.CANCELLED) | models.Q(cancelled_at__isnull=False),
                name="payment_cancelled_at_required",
            ),
            models.CheckConstraint(
                condition=models.Q(status=PaymentStatus.PAID) | models.Q(paid_at__isnull=True, paid_amount__isnull=True, paid_by__isnull=True),
                name="payment_paid_fields_only_when_paid",
            ),
            models.CheckConstraint(
                condition=models.Q(status=PaymentStatus.CANCELLED) | models.Q(cancelled_at__isnull=True),
                name="payment_cancelled_at_only_cancelled",
            ),
        ]
        indexes = [
            models.Index(fields=["sector", "status", "due_date"], name="payment_sector_status_due_idx"),
            models.Index(fields=["supplier", "status", "due_date"], name="pay_supplier_status_due_idx"),
        ]
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"

    def clean(self):
        super().clean()
        errors = {}
        if self.amount is not None and self.amount < 0:
            errors["amount"] = "O valor não pode ser negativo."
        if self.paid_amount is not None and self.paid_amount < 0:
            errors["paid_amount"] = "O valor pago não pode ser negativo."
        if self.document_id and self.document.process_id != self.process_id:
            errors["document"] = "O documento deve pertencer ao mesmo processo do pagamento."
        if self.status == PaymentStatus.PAID and not (self.paid_at and self.paid_amount is not None and self.paid_by_id):
            errors["status"] = "Pagamento pago exige data, valor e responsável pela confirmação."
        if self.status == PaymentStatus.SCHEDULED and not self.scheduled_at:
            errors["scheduled_at"] = "Informe a data do agendamento."
        if self.status == PaymentStatus.CANCELLED and not self.cancelled_at:
            errors["cancelled_at"] = "Informe a data do cancelamento."
        if self.status != PaymentStatus.PAID and (self.paid_at or self.paid_amount is not None or self.paid_by_id):
            errors["paid_at"] = "Dados de confirmação só podem existir em um pagamento pago."
        if self.status != PaymentStatus.CANCELLED and self.cancelled_at:
            errors["cancelled_at"] = "A data de cancelamento só pode existir em um pagamento cancelado."
        if errors:
            raise ValidationError(errors)

    @property
    def is_overdue(self):
        return self.status in {PaymentStatus.PENDING, PaymentStatus.SCHEDULED} and self.due_date < timezone.localdate()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} — {self.supplier}"
