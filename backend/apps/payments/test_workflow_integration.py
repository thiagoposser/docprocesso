from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from apps.processes.models import AdministrativeProcess, ProcessStatus, ProcessType, WorkflowStage, WorkflowTransition
from apps.processes.workflow_services import create_workflow
from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership

from .models import Payment, PaymentMethod, PaymentStatus, Supplier
from .services import InvalidPaymentTransition, confirm_payment, create_payment


class PaymentWorkflowIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workflow_finance")
        self.sector = Sector.objects.create(name="Financeiro workflow payment", code="PAY-WF")
        self.function = OrganizationalFunction.objects.create(name="Financeiro workflow", code="PAY-WF-F")
        UserSectorMembership.objects.create(
            user=self.user, sector=self.sector, function=self.function, is_primary=True
        )
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=[
            "add_payment", "confirm_payment", "view_financial_data", "view_administrativeprocess",
        ]))
        self.workflow = create_workflow(code="payment-integration", name="Pagamento integrado")
        self.processing = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=1, name="Processamento Financeiro",
            is_initial=True, responsible_sector=self.sector, responsible_function=self.function,
        )
        self.payment_stage = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=2, name="Pagamento",
            responsible_sector=self.sector, responsible_function=self.function,
        )
        self.receipt_stage = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=3, name="Comprovante", is_final=True,
            responsible_sector=self.sector, responsible_function=self.function,
        )
        WorkflowTransition.objects.create(
            source_stage=self.processing, destination_stage=self.payment_stage,
            code="encaminhar-pagamento", name="Registrar pagamento",
            authorized_sector=self.sector, authorized_function=self.function,
        )
        WorkflowTransition.objects.create(
            source_stage=self.payment_stage, destination_stage=self.receipt_stage,
            code="confirmar-pagamento", name="Confirmar pagamento",
            authorized_sector=self.sector, authorized_function=self.function,
        )
        process_type = ProcessType.objects.create(name="Pagamento integrado", code="pay-integrated", workflow=self.workflow)
        self.process = AdministrativeProcess.objects.create(
            title="Processo financeiro", process_type=process_type, created_by=self.user,
            origin_sector=self.sector, current_sector=self.sector, status=ProcessStatus.OPEN,
            workflow_version=self.workflow.current_version, current_stage=self.processing,
            responsible_sector=self.sector, responsible_function=self.function,
        )
        self.supplier = Supplier.objects.create(name="Fornecedor workflow", tax_id="12345678901")

    def test_create_and_confirm_advance_exactly_one_financial_stage_atomically(self):
        payment = create_payment(
            actor=self.user, process=self.process, sector=self.sector, supplier=self.supplier,
            description="Serviço", amount=Decimal("10.00"), due_date=timezone.localdate(),
        )
        self.process.refresh_from_db()
        self.assertEqual(payment.stage, self.processing)
        self.assertEqual(payment.workflow_version, self.workflow.current_version)
        self.assertEqual(self.process.current_stage, self.payment_stage)
        confirmed = confirm_payment(
            payment_id=payment.pk, actor=self.user, paid_at=timezone.now(),
            paid_amount=Decimal("10.00"), payment_method=PaymentMethod.PIX,
        )
        self.process.refresh_from_db()
        self.assertEqual(confirmed.status, PaymentStatus.PAID)
        self.assertEqual(self.process.current_stage, self.receipt_stage)
        self.assertEqual(self.process.movements.count(), 2)

    def test_wrong_stage_rejects_without_creating_payment(self):
        AdministrativeProcess.objects.filter(pk=self.process.pk).update(current_stage=self.payment_stage)
        self.process.refresh_from_db()
        with self.assertRaises(InvalidPaymentTransition):
            create_payment(
                actor=self.user, process=self.process, sector=self.sector, supplier=self.supplier,
                description="Inválido", amount=Decimal("10.00"), due_date=timezone.localdate(),
            )
        self.assertFalse(Payment.objects.exists())
