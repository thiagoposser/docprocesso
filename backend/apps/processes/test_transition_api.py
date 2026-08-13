from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership
from apps.documents.models import Attachment, Document, DocumentCategory, DocumentRole
from apps.documents.services import create_attachment

from .models import AdministrativeProcess, ProcessStatus, ProcessType, WorkflowStage, WorkflowTransition
from .workflow_services import create_workflow


class ProcessTransitionApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="transition_api")
        self.outsider = get_user_model().objects.create_user(username="transition_outsider")
        self.other_sector_actor = get_user_model().objects.create_user(username="transition_other_sector")
        self.unlinked_actor = get_user_model().objects.create_user(username="transition_unlinked")
        self.origin = Sector.objects.create(name="Origem API action", code="ACT-O")
        self.destination = Sector.objects.create(name="Destino API action", code="ACT-D")
        self.target_function = OrganizationalFunction.objects.create(name="Aprovador API action", code="ACT-F")
        UserSectorMembership.objects.create(user=self.user, sector=self.origin, is_primary=True)
        UserSectorMembership.objects.create(user=self.user, sector=self.destination)
        UserSectorMembership.objects.create(user=self.outsider, sector=self.origin, is_primary=True)
        UserSectorMembership.objects.create(user=self.other_sector_actor, sector=self.destination, is_primary=True)
        permissions = Permission.objects.filter(codename__in=["view_administrativeprocess", "forward_administrativeprocess"])
        self.user.user_permissions.add(*permissions)
        self.outsider.user_permissions.add(Permission.objects.get(codename="view_administrativeprocess"))
        scoped_permissions = Permission.objects.filter(
            codename__in=["view_administrativeprocess", "forward_administrativeprocess"]
        )
        self.other_sector_actor.user_permissions.add(*scoped_permissions)
        self.unlinked_actor.user_permissions.add(*scoped_permissions)
        self.workflow = create_workflow(code="transition-api", name="Transition API")
        self.source = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=1, name="Solicitação", is_initial=True,
            responsible_sector=self.origin,
        )
        self.target = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=2, name="Aprovação", is_final=True,
            responsible_sector=self.destination, responsible_function=self.target_function,
        )
        self.transition = WorkflowTransition.objects.create(
            source_stage=self.source, destination_stage=self.target, code="aprovar", name="Aprovar",
            authorized_sector=self.origin, requires_note=True, requires_attachment=True,
        )
        process_type = ProcessType.objects.create(name="Action API", code="action-api", workflow=self.workflow)
        self.process = AdministrativeProcess.objects.create(
            title="Ações", process_type=process_type, workflow_version=self.workflow.current_version,
            current_stage=self.source, created_by=self.user, origin_sector=self.origin,
            current_sector=self.origin, status=ProcessStatus.OPEN,
        )
        self.client.force_authenticate(self.user)

    @property
    def available_url(self):
        return reverse("process-available-actions", args=[self.process.pk])

    @property
    def execute_url(self):
        return reverse("process-transitions", args=[self.process.pk])

    def test_lists_only_authorized_actions_with_requirements(self):
        response = self.client.get(self.available_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{
            "action": "aprovar", "label": "Aprovar", "destination_stage": self.target.pk,
            "destination_stage_name": "Aprovação", "requires_note": True,
            "requires_attachment": True, "required_document_role": "", "integration_action": "", "is_return": False,
        }])
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(self.available_url).data, [])

    def test_execution_revalidates_requirements_and_updates_stage(self):
        missing_note = self.client.post(self.execute_url, {"action": "aprovar", "version": 1}, format="json")
        self.assertEqual(missing_note.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        missing_attachment = self.client.post(
            self.execute_url, {"action": "aprovar", "version": 1, "note": "Aprovado"}, format="json"
        )
        self.assertEqual(missing_attachment.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.transition.requires_attachment = False
        self.transition.save()
        executed = self.client.post(
            self.execute_url, {"action": "aprovar", "version": 1, "note": "Aprovado"}, format="json"
        )
        self.assertEqual(executed.status_code, status.HTTP_200_OK)
        self.assertEqual(executed.data["current_stage"], self.target.pk)
        self.assertEqual(executed.data["current_sector"], self.destination.pk)
        self.assertEqual(executed.data["responsible_sector"], self.destination.pk)
        self.assertEqual(executed.data["responsible_function"], self.target_function.pk)
        historical_destination_name = self.destination.name
        historical_function_name = self.target_function.name
        self.destination.name = "Destino renomeado"
        self.destination.active = False
        self.destination.save()
        self.target_function.name = "Função renomeada"
        self.target_function.active = False
        self.target_function.save()
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        timeline = self.client.get(reverse("process-timeline", args=[self.process.pk]))
        self.assertEqual(timeline.status_code, status.HTTP_200_OK)
        fact = timeline.data["results"][0]
        self.assertEqual(fact["transition_code"], "aprovar")
        self.assertEqual(fact["workflow_version_number"], 1)
        self.assertEqual(fact["from_stage_name"], "Solicitação")
        self.assertEqual(fact["to_stage_name"], "Aprovação")
        self.assertEqual(fact["from_responsibility"], self.origin.name)
        self.assertEqual(
            fact["to_responsibility"], f"{historical_destination_name} · {historical_function_name}"
        )

    def test_rejects_illegal_stale_and_terminal_actions(self):
        illegal = self.client.post(self.execute_url, {"action": "inexistente", "version": 1}, format="json")
        self.assertEqual(illegal.status_code, status.HTTP_403_FORBIDDEN)
        self.process.refresh_from_db()
        self.assertEqual((self.process.current_stage, self.process.version), (self.source, 1))
        self.transition.requires_note = False
        self.transition.requires_attachment = False
        self.transition.save()
        stale = self.client.post(self.execute_url, {"action": "aprovar", "version": 99}, format="json")
        self.assertEqual(stale.status_code, status.HTTP_409_CONFLICT)
        self.process.status = ProcessStatus.COMPLETED
        self.process.completed_at = self.process.updated_at
        AdministrativeProcess.objects.filter(pk=self.process.pk).update(
            status=ProcessStatus.COMPLETED, completed_at=self.process.updated_at
        )
        self.assertEqual(self.client.get(self.available_url).data, [])

    def test_manual_calls_cannot_cross_sector_or_bypass_membership(self):
        self.transition.requires_note = False
        self.transition.requires_attachment = False
        self.transition.save()
        for actor in (self.outsider, self.other_sector_actor, self.unlinked_actor):
            with self.subTest(actor=actor.username):
                self.client.force_authenticate(actor)
                response = self.client.post(
                    self.execute_url, {"action": "aprovar", "version": 1}, format="json"
                )
                self.assertIn(response.status_code, {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND})
                self.process.refresh_from_db()
                self.assertEqual((self.process.current_stage, self.process.version), (self.source, 1))
                self.assertFalse(self.process.movements.exists())

    def test_legacy_process_has_no_actions(self):
        legacy = AdministrativeProcess.objects.create(
            title="Legado", process_type=self.process.process_type, created_by=self.user, origin_sector=self.origin,
        )
        self.assertEqual(self.client.get(reverse("process-available-actions", args=[legacy.pk])).data, [])
        response = self.client.post(
            reverse("process-transitions", args=[legacy.pk]), {"action": "aprovar", "version": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_active_attachment_with_configured_document_role(self):
        self.transition.requires_note = False
        self.transition.required_document_role = DocumentRole.PAYMENT_RECEIPT
        self.transition.save()
        category = DocumentCategory.objects.create(name="Comprovantes workflow")
        general = Document.objects.create(
            title="Documento geral", category=category, process=self.process,
            role=DocumentRole.GENERAL, created_by=self.user,
        )
        contextual = create_attachment(
            document=general, actor=self.user, external_url="https://example.com/general.pdf"
        )
        self.assertEqual(contextual.workflow_version, self.workflow.current_version)
        self.assertEqual(contextual.stage, self.source)
        self.assertEqual(contextual.sector, self.origin)
        self.assertEqual(contextual.context_snapshot["document_role"], DocumentRole.GENERAL)
        blocked = self.client.post(self.execute_url, {"action": "aprovar", "version": 1}, format="json")
        self.assertEqual(blocked.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        receipt = Document.objects.create(
            title="Comprovante", category=category, process=self.process,
            role=DocumentRole.PAYMENT_RECEIPT, created_by=self.user,
        )
        create_attachment(document=receipt, actor=self.user, external_url="https://example.com/receipt.pdf")
        allowed = self.client.post(self.execute_url, {"action": "aprovar", "version": 1}, format="json")
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
