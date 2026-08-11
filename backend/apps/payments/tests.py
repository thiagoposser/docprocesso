from datetime import timedelta
from decimal import Decimal
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, DocumentCategory
from apps.notifications.models import Notification, NotificationType
from apps.processes.models import AdministrativeProcess, ProcessType
from apps.sectors.models import Sector, UserSectorMembership

from .models import Payment, PaymentMethod, PaymentStatus, Supplier


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
        payment.payment_method = PaymentMethod.PIX
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
        self.assertTrue({"view_payment", "add_payment", "change_payment", "view_financial_data", "confirm_payment", "schedule_payment", "cancel_payment"}.issubset(codenames))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PaymentApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        media_root = str(cls._overridden_settings["MEDIA_ROOT"])
        super().tearDownClass()
        shutil.rmtree(media_root, ignore_errors=True)

    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="finance_api")
        self.masked_user = users.objects.create_user(username="supplier_api")
        self.outsider = users.objects.create_user(username="finance_outsider")
        self.sector = Sector.objects.create(name="Financeiro API", code="FIN-API")
        self.other_sector = Sector.objects.create(name="Outro financeiro", code="FIN-X")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        UserSectorMembership.objects.create(user=self.outsider, sector=self.other_sector, is_primary=True)
        process_type = ProcessType.objects.create(name="Financeiro API", code="financeiro-api")
        self.process = AdministrativeProcess.objects.create(
            title="Despesa API", process_type=process_type, created_by=self.user,
            origin_sector=self.sector, current_sector=self.sector,
        )
        self.supplier = Supplier.objects.create(
            name="Fornecedor API", tax_id="12345678901", bank_name="Banco", bank_branch="1", bank_account="2",
        )
        finance_permissions = Permission.objects.filter(codename__in={
            "view_administrativeprocess", "view_supplier", "add_supplier", "change_supplier",
            "view_payment", "add_payment", "change_payment", "view_financial_data",
            "schedule_payment", "confirm_payment", "cancel_payment",
            "view_paymentreceipt", "manage_payment_receipt",
            "view_document",
        })
        self.user.user_permissions.add(*finance_permissions)
        self.outsider.user_permissions.add(*finance_permissions)
        self.masked_user.user_permissions.add(Permission.objects.get(codename="view_supplier"))

    def payload(self, **overrides):
        values = {
            "process": self.process.pk, "sector": self.sector.pk, "supplier": self.supplier.pk,
            "description": "Serviço mensal", "amount": "150.25",
            "due_date": (timezone.localdate() + timedelta(days=10)).isoformat(),
        }
        values.update(overrides)
        return values

    def test_supplier_masks_sensitive_fields_without_financial_permission(self):
        self.client.force_authenticate(self.masked_user)
        response = self.client.get(reverse("supplier-detail", args=[self.supplier.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tax_id_masked"], "***8901")
        self.assertNotIn("tax_id", response.data)
        self.assertNotIn("bank_account", response.data)
        self.assertNotIn("email", response.data)
        self.assertNotIn("phone", response.data)

        self.client.force_authenticate(self.user)
        authorized = self.client.get(reverse("supplier-detail", args=[self.supplier.pk]))
        self.assertEqual(authorized.data["tax_id"], "12345678901")
        self.assertEqual(authorized.data["bank_account"], "2")

        created = self.client.post(
            reverse("supplier-list"), {"name": "Novo", "tax_id": "98.765.432/0001-10", "active": True}, format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data["tax_id"], "98765432000110")
        invalid = self.client.post(reverse("supplier-list"), {"name": "Inválido", "tax_id": "123"}, format="json")
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_crud_protects_workflow_fields_and_audit_values(self):
        self.client.force_authenticate(self.user)
        created = self.client.post(reverse("payment-list"), self.payload(), format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        payment_id = created.data["id"]
        self.assertEqual(created.data["status"], PaymentStatus.PENDING)
        rejected = self.client.patch(reverse("payment-detail", args=[payment_id]), {"status": PaymentStatus.PAID}, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        updated = self.client.patch(reverse("payment-detail", args=[payment_id]), {"description": "Serviço atualizado"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)

        from apps.audit.models import AuditLog
        serialized_audit = str(list(AuditLog.objects.filter(entity_id=str(payment_id)).values("old_values", "new_values")))
        self.assertNotIn("bank_account", serialized_audit)
        self.assertNotIn("tax_id", serialized_audit)
        self.assertNotIn("amount", serialized_audit)

    def test_filters_and_sector_isolation(self):
        first = Payment.objects.create(created_by=self.user, **{k: v for k, v in self.payload().items() if k not in {"process", "sector", "supplier"}}, process=self.process, sector=self.sector, supplier=self.supplier)
        Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Outro", amount=Decimal("500.00"), due_date=timezone.localdate() + timedelta(days=30),
        )
        self.client.force_authenticate(self.user)
        filtered = self.client.get(reverse("payment-list"), {"status": "PENDING", "supplier": self.supplier.pk, "process": self.process.pk, "min_amount": "400", "due_from": timezone.localdate().isoformat()})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["count"], 1)

        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(reverse("payment-list")).data["count"], 0)
        self.assertEqual(self.client.get(reverse("payment-detail", args=[first.pk])).status_code, status.HTTP_404_NOT_FOUND)
        cross_create = self.client.post(reverse("payment-list"), self.payload(), format="json")
        self.assertEqual(cross_create.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deadline_filters_summary_and_notifications_are_scoped_and_idempotent(self):
        today = timezone.localdate()
        payments = {
            key: Payment.objects.create(
                process=self.process, sector=self.sector, supplier=self.supplier,
                created_by=self.user, description=key, amount=Decimal("25.00"),
                due_date=due_date,
            )
            for key, due_date in {
                "overdue": today - timedelta(days=1),
                "today": today,
                "upcoming": today + timedelta(days=7),
                "future": today + timedelta(days=8),
            }.items()
        }
        Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier,
            created_by=self.user, description="paid", amount=Decimal("25.00"),
            due_date=today - timedelta(days=2), status=PaymentStatus.PAID,
            paid_at=timezone.now(), paid_amount=Decimal("25.00"),
            payment_method=PaymentMethod.PIX, paid_by=self.user,
        )
        self.client.force_authenticate(self.user)

        for deadline in ("overdue", "today", "upcoming"):
            response = self.client.get(reverse("payment-list"), {"deadline": deadline})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual([item["id"] for item in response.data["results"]], [payments[deadline].pk])
        self.assertEqual(
            self.client.get(reverse("payment-list"), {"deadline": "invalid"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        summary_url = reverse("payment-deadline-summary")
        first = self.client.get(summary_url)
        second = self.client.get(summary_url)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data, {"overdue": 1, "today": 1, "upcoming": 1})
        self.assertEqual(second.data, first.data)
        notifications = Notification.objects.filter(user=self.user, type=NotificationType.PAYMENT)
        self.assertEqual(notifications.count(), 3)
        self.assertFalse(any("25" in item.message for item in notifications))
        self.assertFalse(Notification.objects.filter(user=self.outsider, type=NotificationType.PAYMENT).exists())

        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(summary_url).data, {"overdue": 0, "today": 0, "upcoming": 0})

    def test_payment_requires_financial_and_process_permissions(self):
        self.client.force_authenticate(self.masked_user)
        self.assertEqual(self.client.get(reverse("payment-list")).status_code, status.HTTP_403_FORBIDDEN)

    def test_schedule_confirm_and_retry_are_atomic_and_traced(self):
        payment = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Fluxo", amount=Decimal("100.00"), due_date=timezone.localdate() + timedelta(days=5),
        )
        self.client.force_authenticate(self.user)
        scheduled = self.client.post(
            reverse("payment-schedule", args=[payment.pk]),
            {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()}, format="json",
        )
        self.assertEqual(scheduled.status_code, status.HTTP_200_OK, scheduled.data)
        confirmed = self.client.post(
            reverse("payment-confirm", args=[payment.pk]),
            {"paid_at": timezone.now().isoformat(), "paid_amount": "100.00", "payment_method": PaymentMethod.PIX}, format="json",
        )
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)
        self.assertEqual(confirmed.data["status"], PaymentStatus.PAID)
        event_count = self.process.events.count()
        retry = self.client.post(
            reverse("payment-confirm", args=[payment.pk]),
            {"paid_at": timezone.now().isoformat(), "paid_amount": "100.00", "payment_method": PaymentMethod.PIX}, format="json",
        )
        self.assertEqual(retry.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.process.events.count(), event_count)

    def test_cancel_requires_reason_and_terminal_process_policy_is_explicit(self):
        payment = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Cancelar", amount=Decimal("10.00"), due_date=timezone.localdate() + timedelta(days=2),
        )
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(reverse("payment-cancel", args=[payment.pk]), {"reason": ""}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        cancelled = self.client.post(reverse("payment-cancel", args=[payment.pk]), {"reason": "Duplicidade"}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelled.data["cancellation_reason"], "Duplicidade")

        blocked = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Bloqueado", amount=Decimal("10.00"), due_date=timezone.localdate() + timedelta(days=2),
        )
        self.process.status = "ARCHIVED"; self.process.archived_at = timezone.now(); self.process.save()
        response = self.client.post(
            reverse("payment-schedule", args=[blocked.pk]),
            {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_event_failure_rolls_back_confirmation(self):
        from unittest.mock import patch
        from .services import confirm_payment

        payment = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Rollback", amount=Decimal("75.00"), due_date=timezone.localdate() + timedelta(days=2),
        )
        with patch("apps.payments.services.append_process_event", side_effect=RuntimeError("event failure")):
            with self.assertRaises(RuntimeError):
                confirm_payment(
                    payment_id=payment.pk, actor=self.user, paid_at=timezone.now(),
                    paid_amount=Decimal("75.00"), payment_method=PaymentMethod.BANK_TRANSFER,
                )
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertIsNone(payment.paid_at)

    def test_action_locks_payment_row_and_requires_specific_permission(self):
        from .services import schedule_payment

        payment = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Lock", amount=Decimal("20.00"), due_date=timezone.localdate() + timedelta(days=2),
        )
        with CaptureQueriesContext(connection) as queries:
            schedule_payment(
                payment_id=payment.pk, actor=self.user,
                scheduled_at=timezone.now() + timedelta(days=1),
            )
        self.assertTrue(any("FOR UPDATE" in query["sql"].upper() for query in queries.captured_queries))

        limited = get_user_model().objects.create_user(username="finance_limited")
        UserSectorMembership.objects.create(user=limited, sector=self.sector, is_primary=True)
        limited.user_permissions.add(*Permission.objects.filter(codename__in={
            "view_administrativeprocess", "view_payment", "view_financial_data",
        }))
        self.client.force_authenticate(limited)
        self.assertEqual(
            self.client.post(
                reverse("payment-confirm", args=[payment.pk]),
                {"paid_at": timezone.now().isoformat(), "paid_amount": "20.00", "payment_method": PaymentMethod.PIX},
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_receipts_are_multiple_secure_and_logically_removed(self):
        payment = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Com comprovantes", amount=Decimal("30.00"), due_date=timezone.localdate(),
            status=PaymentStatus.PAID, paid_at=timezone.now(), paid_amount=Decimal("30.00"),
            payment_method=PaymentMethod.PIX, paid_by=self.user,
        )
        self.client.force_authenticate(self.user)
        responses = [
            self.client.post(
                reverse("payment-receipts", args=[payment.pk]),
                {"file": SimpleUploadedFile(f"comprovante-{index}.pdf", b"%PDF-1.4", content_type="application/pdf")},
                format="multipart",
            )
            for index in (1, 2)
        ]
        self.assertTrue(all(response.status_code == status.HTTP_201_CREATED for response in responses), responses)
        self.assertEqual(payment.receipts.count(), 2)
        from apps.audit.models import AuditLog
        self.assertEqual(AuditLog.objects.filter(entity_type="payments.PaymentReceipt").count(), 2)
        attachment_data = responses[0].data["attachment"]
        self.assertNotIn("file", attachment_data)
        self.assertNotIn("external_url", attachment_data)
        attachment_id = attachment_data["id"]
        self.assertNotIn("comprovante-1", payment.receipts.first().attachment.file.name)
        self.assertEqual(self.client.get(reverse("attachment-download", args=[attachment_id])).status_code, status.HTTP_200_OK)
        self.assertFalse(any(item["id"] == payment.receipts.first().attachment.document_id for item in self.client.get(reverse("document-list")).data["results"]))
        process_documents = self.client.get(reverse("process-documents", args=[self.process.pk]))
        self.assertFalse(any(item["id"] == payment.receipts.first().attachment.document_id for item in process_documents.data["results"]))
        self.assertEqual(self.client.get(reverse("core:dashboard")).data["total_documents"], 0)

        deactivated = self.client.patch(reverse("attachment-deactivate", args=[attachment_id]), {}, format="json")
        self.assertEqual(deactivated.status_code, status.HTTP_200_OK)
        self.assertFalse(deactivated.data["active"])
        self.assertEqual(payment.receipts.count(), 2)
        self.assertEqual(self.process.events.filter(title="Comprovante anexado").count(), 2)

        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(reverse("payment-receipts", args=[payment.pk])).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse("attachment-download", args=[attachment_id])).status_code, status.HTTP_404_NOT_FOUND)

    def test_receipt_requires_paid_payment_but_allows_completed_process(self):
        payment = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=self.supplier, created_by=self.user,
            description="Política", amount=Decimal("10.00"), due_date=timezone.localdate(),
        )
        self.client.force_authenticate(self.user)
        pending = self.client.post(
            reverse("payment-receipts", args=[payment.pk]),
            {"file": SimpleUploadedFile("pendente.pdf", b"%PDF", content_type="application/pdf")}, format="multipart",
        )
        self.assertEqual(pending.status_code, status.HTTP_400_BAD_REQUEST)
        payment.status = PaymentStatus.PAID; payment.paid_at = timezone.now(); payment.paid_amount = payment.amount
        payment.payment_method = PaymentMethod.BOLETO; payment.paid_by = self.user; payment.save()
        self.process.status = "COMPLETED"; self.process.completed_at = timezone.now(); self.process.save()
        completed = self.client.post(
            reverse("payment-receipts", args=[payment.pk]),
            {"file": SimpleUploadedFile("concluido.pdf", b"%PDF", content_type="application/pdf")}, format="multipart",
        )
        self.assertEqual(completed.status_code, status.HTTP_201_CREATED, completed.data)
