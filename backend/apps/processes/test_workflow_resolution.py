from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership

from .models import ProcessType, WorkflowStage
from .workflow_services import create_workflow


class ProcessWorkflowResolutionTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workflow_resolution")
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=["add_administrativeprocess", "view_administrativeprocess"]
        ))
        self.sector = Sector.objects.create(name="Origem resolução", code="RES-O")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        self.client.force_authenticate(self.user)

    def configure(self, code="resolver", sector=None):
        workflow = create_workflow(code=code, name=code.title())
        stage = WorkflowStage.objects.create(
            workflow_version=workflow.current_version, order=1, name="Inicial", is_initial=True,
            responsible_sector=sector or self.sector,
        )
        process_type = ProcessType.objects.create(name=code.title(), code=code, workflow=workflow)
        return workflow, stage, process_type

    def test_creation_pins_workflow_version_and_initial_stage(self):
        workflow, stage, process_type = self.configure()
        function = OrganizationalFunction.objects.create(name="Solicitante resolução", code="RES-F")
        stage.responsible_function = function
        stage.save()
        response = self.client.post(reverse("process-list"), {"title": "Com fluxo", "process_type": process_type.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["workflow_version"], workflow.current_version_id)
        self.assertEqual(response.data["current_stage"], stage.pk)
        self.assertEqual(response.data["current_stage_name"], "Inicial")
        self.assertEqual(response.data["responsible_sector"], self.sector.pk)
        self.assertEqual(response.data["responsible_function"], function.pk)

    def test_rejects_missing_ambiguous_inactive_and_ineligible_workflow(self):
        no_flow = ProcessType.objects.create(name="Sem fluxo", code="sem-fluxo")
        missing = self.client.post(reverse("process-list"), {"title": "Sem", "process_type": no_flow.pk}, format="json")
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

        first, _, process_type = self.configure("primeiro")
        second, _, _ = self.configure("segundo")
        process_type.workflow = None
        process_type.save(update_fields=["workflow"])
        ambiguous = self.client.post(reverse("process-list"), {"title": "Ambíguo", "process_type": process_type.pk}, format="json")
        self.assertEqual(ambiguous.status_code, status.HTTP_400_BAD_REQUEST)

        first.active = False
        first.save(update_fields=["active"])
        process_type.workflow = first
        process_type.save(update_fields=["workflow"])
        inactive = self.client.post(reverse("process-list"), {"title": "Inativo", "process_type": process_type.pk}, format="json")
        self.assertEqual(inactive.status_code, status.HTTP_400_BAD_REQUEST)

        other = Sector.objects.create(name="Outra origem", code="RES-X")
        third, _, other_type = self.configure("terceiro", sector=other)
        ineligible = self.client.post(reverse("process-list"), {"title": "Inelegível", "process_type": other_type.pk}, format="json")
        self.assertEqual(ineligible.status_code, status.HTTP_400_BAD_REQUEST)

    def test_process_keeps_pinned_version_after_workflow_changes(self):
        workflow, stage, process_type = self.configure("fixado")
        created = self.client.post(reverse("process-list"), {"title": "Fixado", "process_type": process_type.pk}, format="json")
        from .workflow_services import update_workflow
        update_workflow(workflow=workflow, description="Nova versão")
        detail = self.client.get(reverse("process-detail", args=[created.data["id"]]))
        self.assertEqual(detail.data["workflow_version"], stage.workflow_version_id)
        self.assertEqual(detail.data["workflow_version_number"], 1)
