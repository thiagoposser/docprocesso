from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.documents.models import Document, DocumentCategory
from apps.processes.models import AdministrativeProcess, ProcessType
from apps.sectors.models import Sector

from .models import Payment, PaymentStatus, Supplier


class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="payment_owner")
        self.sector = Sector.objects.create(name="Financeiro", code="FIN")
        self.process_type = ProcessType.objects.create(name="Pagamento", code="pagamento")
        self.process = AdministrativeProcess.objects.create(
            title="Aquisição", process_type=self.process_type, created_by=self.user,
            origin_sector=self.sector, current_sector=self.sector,
        )
        self.supplier = Supplier.objects.create(
            name="Fornecedor Exemplo", tax_id="12.345.678/0001-90",
            bank_name="Banco", bank_branch="0001", bank_account="12345-6",
        )

    def payment(self, **overrides):
        values = {
            "process": self.process, "sector": self.sector, "supplier": self.supplier,
            "description": "Nota fiscal", "amount": Decimal("1234567890.12"),
            "due_date": timezone.localdate() + timedelta(days=5), "created_by": self.user,
        }
        values.update(overrides)
        return Payment(**values)

    def test_normalizes_tax_id_and_does_not_expose_sensitive_data_in_string(self):
        self.assertEqual(self.supplier.tax_id, "12345678000190")
        self.assertEqual(str(self.supplier), "Fornecedor Exemplo")
        with self.assertRaises(ValidationError):
            Supplier.objects.create(name="Inválido", tax_id="123")
        with self.assertRaises(ValidationError):
            Supplier.objects.create(name="Banco incompleto", tax_id="12345678901", bank_name="Banco")

    def test_preserves_decimal_precision_and_derives_overdue(self):
        payment = self.payment(due_date=timezone.localdate() - timedelta(days=1))
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal("1234567890.12"))
        self.assertTrue(payment.is_overdue)
        payment.status = PaymentStatus.PAID
        payment.paid_at = timezone.now()
        payment.paid_amount = payment.amount
        payment.paid_by = self.user
        payment.save()
        self.assertFalse(payment.is_overdue)

    def test_paid_scheduled_cancelled_and_nonnegative_coherence(self):
        with self.assertRaises(ValidationError):
            self.payment(status=PaymentStatus.PAID).save()
        with self.assertRaises(ValidationError):
            self.payment(status=PaymentStatus.SCHEDULED).save()
        with self.assertRaises(ValidationError):
            self.payment(status=PaymentStatus.CANCELLED).save()
        with self.assertRaises(ValidationError):
            self.payment(amount=Decimal("-0.01")).save()
        with self.assertRaises(ValidationError):
            self.payment(paid_amount=Decimal("1.00")).save()

    def test_database_constraints_reject_invalid_bulk_insert(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payment.objects.bulk_create([self.payment(amount=Decimal("-1.00"))])
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payment.objects.bulk_create([self.payment(status=PaymentStatus.PAID)])

    def test_document_must_belong_to_same_process_and_foreign_keys_are_protected(self):
        other = AdministrativeProcess.objects.create(
            title="Outro", process_type=self.process_type, created_by=self.user,
            origin_sector=self.sector, current_sector=self.sector,
        )
        category = DocumentCategory.objects.create(name="Fiscal")
        document = Document.objects.create(title="NF", category=category, process=other, created_by=self.user)
        with self.assertRaises(ValidationError):
            self.payment(document=document).save()
        payment = self.payment(); payment.save()
        with self.assertRaises(ProtectedError):
            self.supplier.delete()
        with self.assertRaises(ProtectedError):
            self.process.delete()

    def test_declares_financial_permissions(self):
        codenames = set(Permission.objects.filter(content_type__app_label="payments").values_list("codename", flat=True))
        self.assertTrue({"view_payment", "add_payment", "change_payment", "view_financial_data", "confirm_payment"}.issubset(codenames))
