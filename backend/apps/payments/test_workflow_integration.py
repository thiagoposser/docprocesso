from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.processes.models import AdministrativeProcess, ProcessStatus, ProcessType, WorkflowStage, WorkflowTransition
from apps.processes.workflow_services import create_workflow
from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership

from .models import Payment, PaymentMethod, PaymentStatus, Supplier
from .services import InvalidPaymentTransition, confirm_payment, create_payment


class PaymentWorkflowIntegrationTests(APITestCase):
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

    def payment_payload(self):
        return {
            "process": self.process.pk, "sector": self.sector.pk, "supplier": self.supplier.pk,
            "description": "Serviço", "amount": "10.00", "due_date": str(timezone.localdate()),
        }

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

    def test_available_action_routes_financial_work_and_generic_transition_cannot_skip_it(self):
        self.client.force_authenticate(self.user)
        available = self.client.get(reverse("process-available-actions", args=[self.process.pk]))
        self.assertEqual(available.status_code, status.HTTP_200_OK)
        self.assertEqual(available.data[0]["integration_action"], "create_payment")
        blocked = self.client.post(
            reverse("process-transitions", args=[self.process.pk]),
            {"action": "encaminhar-pagamento", "version": 1}, format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.process.refresh_from_db()
        self.assertEqual((self.process.current_stage, self.process.version), (self.processing, 1))
        self.assertFalse(Payment.objects.exists())

    def test_financial_permission_without_eligible_function_rolls_back_api_creation(self):
        wrong_function = OrganizationalFunction.objects.create(name="Função indevida", code="PAY-WF-WRONG")
        actor = get_user_model().objects.create_user(username="workflow_wrong_function")
        UserSectorMembership.objects.create(
            user=actor, sector=self.sector, function=wrong_function, is_primary=True
        )
        actor.user_permissions.add(*Permission.objects.filter(codename__in=[
            "add_payment", "view_financial_data", "view_administrativeprocess",
        ]))
        self.client.force_authenticate(actor)
        response = self.client.post(reverse("payment-list"), self.payment_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.exists())
        self.process.refresh_from_db()
        self.assertEqual((self.process.current_stage, self.process.version), (self.processing, 1))
