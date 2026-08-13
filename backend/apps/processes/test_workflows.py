from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import ProtectedError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sectors.models import OrganizationalFunction, Sector

from .models import AdministrativeWorkflow, WorkflowStage, WorkflowVersion
from .workflow_services import create_workflow, update_workflow


class AdministrativeWorkflowApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workflow_admin")
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=[
                "view_administrativeworkflow", "add_administrativeworkflow", "change_administrativeworkflow",
                "view_workflowstage", "add_workflowstage", "change_workflowstage",
            ]
        ))
        self.client.force_authenticate(self.user)

    def test_creates_and_versions_workflow_without_rewriting_history(self):
        created = self.client.post(reverse("workflow-list"), {
            "code": "compras", "name": "Compras", "description": "Versão inicial", "active": True,
        }, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["version"], 1)

        detail = reverse("workflow-detail", args=[created.data["id"]])
        updated = self.client.patch(detail, {"description": "Versão revisada"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["version"], 2)
        versions = WorkflowVersion.objects.filter(workflow_id=created.data["id"]).order_by("version")
        self.assertEqual(list(versions.values_list("description", flat=True)), ["Versão inicial", "Versão revisada"])

    def test_inactivation_does_not_publish_or_remove_version(self):
        workflow = AdministrativeWorkflow.objects.create(code="apuracao")
        version = WorkflowVersion.objects.create(workflow=workflow, version=1, name="Apuração")
        workflow.current_version = version
        workflow.save()
        response = self.client.patch(reverse("workflow-detail", args=[workflow.pk]), {"active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["active"])
        self.assertEqual(response.data["version"], 1)
        with self.assertRaises(ProtectedError):
            version.delete()

    def test_requires_specific_permissions(self):
        self.user.user_permissions.clear()
        self.assertEqual(self.client.get(reverse("workflow-list")).status_code, status.HTTP_403_FORBIDDEN)

    def test_rejects_code_change_and_delete(self):
        response = self.client.post(reverse("workflow-list"), {"code": "contratos", "name": "Contratos"}, format="json")
        detail = reverse("workflow-detail", args=[response.data["id"]])
        changed = self.client.patch(detail, {"code": "outro"}, format="json")
        self.assertEqual(changed.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(self.client.delete(detail).status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))


class WorkflowStageApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="stage_admin")
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=["view_workflowstage", "add_workflowstage", "change_workflowstage"]
        ))
        self.client.force_authenticate(self.user)
        self.workflow = create_workflow(code="compras-stage", name="Compras")
        self.sector = Sector.objects.create(name="Compras", code="COMP-STAGE")
        self.function = OrganizationalFunction.objects.create(name="Aprovador", code="APROV-STAGE")

    def payload(self, **changes):
        data = {
            "workflow_version": self.workflow.current_version_id, "order": 1, "name": "Solicitação",
            "is_initial": True, "is_final": False, "responsible_sector": self.sector.pk,
            "responsible_function": self.function.pk, "requires_manager": False,
        }
        data.update(changes)
        return data

    def test_creates_and_lists_ordered_stages(self):
        first = self.client.post(reverse("workflow-stage-list"), self.payload(), format="json")
        second = self.client.post(reverse("workflow-stage-list"), self.payload(
            order=2, name="Finalização", is_initial=False, is_final=True
        ), format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        listed = self.client.get(reverse("workflow-stage-list"), {"workflow": self.workflow.pk})
        self.assertEqual([item["name"] for item in listed.data["results"]], ["Solicitação", "Finalização"])

    def test_rejects_duplicate_order_and_initial_stage(self):
        self.client.post(reverse("workflow-stage-list"), self.payload(), format="json")
        for changes in ({"name": "Mesma ordem", "is_initial": False}, {"order": 2, "name": "Outra inicial"}):
            response = self.client.post(reverse("workflow-stage-list"), self.payload(**changes), format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_missing_or_inactive_responsibility(self):
        missing = self.client.post(reverse("workflow-stage-list"), self.payload(
            responsible_sector=None, responsible_function=None
        ), format="json")
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.sector.active = False
        self.sector.save()
        inactive = self.client.post(reverse("workflow-stage-list"), self.payload(responsible_function=None), format="json")
        self.assertEqual(inactive.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_version_clones_stages_and_historical_stage_is_read_only(self):
        created = self.client.post(reverse("workflow-stage-list"), self.payload(), format="json")
        old_version = self.workflow.current_version
        update_workflow(workflow=self.workflow, description="Revisado")
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.current_version.stages.count(), 1)
        self.assertEqual(old_version.stages.count(), 1)
        changed = self.client.patch(
            reverse("workflow-stage-detail", args=[created.data["id"]]), {"name": "Alterada"}, format="json"
        )
        self.assertEqual(changed.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_stage_permissions(self):
        self.user.user_permissions.clear()
        self.assertEqual(self.client.get(reverse("workflow-stage-list")).status_code, status.HTTP_403_FORBIDDEN)
