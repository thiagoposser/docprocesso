from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import ProtectedError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AdministrativeWorkflow, WorkflowVersion


class AdministrativeWorkflowApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workflow_admin")
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=["view_administrativeworkflow", "add_administrativeworkflow", "change_administrativeworkflow"]
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
