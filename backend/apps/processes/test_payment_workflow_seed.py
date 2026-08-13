from io import StringIO

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership

from .models import AdministrativeWorkflow, ProcessType, WorkflowStage, WorkflowTransition
from .services import create_process


class PaymentWorkflowSeedTests(TestCase):
    def setUp(self):
        self.requester = Sector.objects.create(name="Protocolo seed", code="SEED-PROTO")
        self.management = Sector.objects.create(name="Gerência seed", code="SEED-GER")
        self.finance = Sector.objects.create(name="Financeiro seed", code="SEED-FIN")
        self.arguments = {
            "requester_sector_code": self.requester.code,
            "management_sector_code": self.management.code,
            "finance_sector_code": self.finance.code,
            "stdout": StringIO(),
        }

    def test_seed_is_idempotent_and_builds_valid_payment_graph(self):
        call_command("seed_payment_workflow", **self.arguments)
        call_command("seed_payment_workflow", **self.arguments)

        workflow = AdministrativeWorkflow.objects.get(code="pagamento-administrativo")
        self.assertEqual(workflow.versions.count(), 1)
        stages = workflow.current_version.stages.order_by("order")
        self.assertEqual(stages.count(), 6)
        self.assertEqual(stages.filter(is_initial=True).count(), 1)
        self.assertEqual(stages.filter(is_final=True).count(), 1)
        self.assertEqual(WorkflowTransition.objects.filter(source_stage__workflow_version=workflow.current_version).count(), 9)
        self.assertEqual(
            set(WorkflowTransition.objects.filter(is_return=True).values_list("code", flat=True)),
            {"devolver-solicitante", "devolver-gerencia", "devolver-pagamento", "reabrir-comprovante"},
        )
        receipt = WorkflowTransition.objects.get(code="anexar-comprovante")
        self.assertTrue(receipt.requires_attachment)
        self.assertEqual(receipt.authorized_function.code, "FINANCEIRO")
        self.assertEqual(receipt.destination_stage.name, "Finalização")
        process_type = ProcessType.objects.get(code="pagamento-administrativo")
        self.assertEqual(process_type.workflow, workflow)
        self.assertEqual(OrganizationalFunction.objects.filter(code__in=["ASSISTENTE", "GERENTE", "FINANCEIRO"]).count(), 3)
        requester = get_user_model().objects.create_user(username="payment_seed_requester")
        UserSectorMembership.objects.create(
            user=requester, sector=self.requester,
            function=OrganizationalFunction.objects.get(code="ASSISTENTE"), is_primary=True,
        )
        requester.user_permissions.add(Permission.objects.get(codename="add_administrativeprocess"))
        process = create_process(user=requester, title="Pagamento de teste", process_type=process_type)
        self.assertEqual(process.workflow_version, workflow.current_version)
        self.assertEqual(process.current_stage, stages.get(is_initial=True))

    def test_seed_uses_codes_and_does_not_overwrite_existing_stage(self):
        call_command("seed_payment_workflow", **self.arguments)
        workflow = AdministrativeWorkflow.objects.get(code="pagamento-administrativo")
        stage = WorkflowStage.objects.get(workflow_version=workflow.current_version, order=2)
        WorkflowStage.objects.filter(pk=stage.pk).update(name="Configuração local")

        with self.assertRaisesMessage(Exception, "nenhuma configuração foi sobrescrita"):
            call_command("seed_payment_workflow", **self.arguments)
        stage.refresh_from_db()
        self.assertEqual(stage.name, "Configuração local")
