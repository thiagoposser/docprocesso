from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership

from .models import AdministrativeProcess, ProcessMovement, ProcessStatus, ProcessType, WorkflowStage, WorkflowTransition
from .workflow_execution import TransitionDenied, UnresolvedTransitionSector, execute_semantic_movement
from .workflow_services import create_workflow


class SemanticMovementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="semantic_actor")
        self.origin = Sector.objects.create(name="Origem semântica", code="SEM-O")
        self.destination = Sector.objects.create(name="Destino semântico", code="SEM-D")
        UserSectorMembership.objects.create(user=self.user, sector=self.origin, is_primary=True)
        UserSectorMembership.objects.create(user=self.user, sector=self.destination)
        self.user.user_permissions.add(Permission.objects.get(codename="forward_administrativeprocess"))
        process_type = ProcessType.objects.create(name="Semântico", code="semantico")
        self.process = AdministrativeProcess.objects.create(
            title="Movimento semântico", process_type=process_type, created_by=self.user,
            origin_sector=self.origin, current_sector=self.origin, status=ProcessStatus.OPEN,
        )
        self.workflow = create_workflow(code="semantic-flow", name="Semântico")
        self.source = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=1, name="Origem", responsible_sector=self.origin,
        )
        self.target = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=2, name="Destino", responsible_sector=self.destination,
        )
        self.transition = WorkflowTransition.objects.create(
            source_stage=self.source, destination_stage=self.target, code="enviar", name="Enviar",
            authorized_sector=self.origin,
        )

    def execute(self, **changes):
        arguments = {
            "user": self.user, "process_id": self.process.pk, "transition_id": self.transition.pk,
            "current_stage_id": self.source.pk, "expected_process_version": 1,
            "expected_workflow_version_id": self.workflow.current_version_id,
        }
        arguments.update(changes)
        return execute_semantic_movement(**arguments)

    def test_resolves_destination_from_transition_and_preserves_movement_history(self):
        updated = self.execute()
        self.assertEqual(updated.current_sector, self.destination)
        movement = ProcessMovement.objects.get(process=self.process)
        self.assertEqual(movement.to_sector, self.destination)

    def test_rejects_stage_jump_and_destination_without_sector(self):
        wrong = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=3, name="Outro", responsible_sector=self.destination,
        )
        with self.assertRaises(TransitionDenied):
            self.execute(current_stage_id=wrong.pk)
        function = OrganizationalFunction.objects.create(name="Função sem setor", code="SEM-FUNC")
        function_only = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=4, name="Sem setor", responsible_function=function,
        )
        WorkflowTransition.objects.filter(pk=self.transition.pk).update(destination_stage=function_only)
        with self.assertRaises(UnresolvedTransitionSector):
            self.execute()

    def test_legacy_destination_endpoint_cannot_bypass_engine(self):
        client = APIClient()
        client.force_authenticate(self.user)
        self.user.user_permissions.add(Permission.objects.get(codename="view_administrativeprocess"))
        response = client.post(
            reverse("process-forward", args=[self.process.pk]),
            {"version": 1, "destination": self.destination.pk}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.process.refresh_from_db()
        self.assertEqual(self.process.current_sector, self.origin)
