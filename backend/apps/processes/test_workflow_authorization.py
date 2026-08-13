from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership

from .models import ProcessStatus, WorkflowStage, WorkflowTransition
from .workflow_execution import TransitionDenied, TransitionVersionConflict, authorize_transition_execution
from .workflow_policies import available_transitions, evaluate_transition_authorization
from .workflow_services import create_workflow


class WorkflowAuthorizationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workflow_actor")
        self.permission = Permission.objects.get(codename="forward_administrativeprocess")
        self.user.user_permissions.add(self.permission)
        self.sector = Sector.objects.create(name="Financeiro auth", code="FIN-AUTH")
        self.other_sector = Sector.objects.create(name="Outro auth", code="OUT-AUTH")
        self.function = OrganizationalFunction.objects.create(name="Analista auth", code="AN-AUTH")
        self.other_function = OrganizationalFunction.objects.create(name="Outro auth", code="OUTF-AUTH")
        self.membership = UserSectorMembership.objects.create(
            user=self.user, sector=self.sector, function=self.function, is_primary=True
        )
        self.workflow = create_workflow(code="authorization", name="Autorização")
        self.source = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=1, name="Origem",
            responsible_sector=self.sector, responsible_function=self.function,
        )
        self.destination = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=2, name="Destino",
            responsible_sector=self.other_sector,
        )
        self.transition = WorkflowTransition.objects.create(
            source_stage=self.source, destination_stage=self.destination, code="aprovar", name="Aprovar",
            authorized_sector=self.sector, authorized_function=self.function,
        )

    def decide(self, **changes):
        arguments = {
            "user": self.user, "transition": self.transition, "current_stage": self.source,
            "process_status": ProcessStatus.IN_PROGRESS, "permission": "processes.forward_administrativeprocess",
        }
        arguments.update(changes)
        return evaluate_transition_authorization(**arguments)

    def test_allows_only_combined_permission_sector_and_function(self):
        self.assertTrue(self.decide().allowed)
        self.membership.function = self.other_function
        self.membership.save()
        self.assertEqual(self.decide().reason, "eligible_membership_required")
        self.user.user_permissions.clear()
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.assertEqual(self.decide(user=self.user).reason, "permission_required")

    def test_denies_wrong_stage_inactive_transition_and_terminal_process(self):
        self.assertEqual(self.decide(current_stage=self.destination).reason, "transition_not_available_from_current_stage")
        self.transition.active = False
        self.transition.save()
        self.assertEqual(self.decide().reason, "inactive_or_invalid_transition")
        self.transition.active = True
        self.transition.save()
        self.assertEqual(self.decide(process_status=ProcessStatus.COMPLETED).reason, "terminal_process")

    def test_requirements_are_enforced(self):
        self.transition.requires_note = True
        self.transition.requires_attachment = True
        self.transition.save()
        self.assertEqual(self.decide().reason, "note_required")
        self.assertEqual(self.decide(note="Analisado").reason, "attachment_required")
        self.assertTrue(self.decide(note="Analisado", has_attachment=True).allowed)

    def test_available_and_execution_share_same_policy(self):
        self.assertEqual(available_transitions(
            self.user, current_stage=self.source, process_status=ProcessStatus.IN_PROGRESS,
            permission="processes.forward_administrativeprocess",
        ), [self.transition])
        authorized = authorize_transition_execution(
            user=self.user, transition_id=self.transition.pk, current_stage_id=self.source.pk,
            expected_workflow_version_id=self.workflow.current_version_id,
            process_status=ProcessStatus.IN_PROGRESS, permission="processes.forward_administrativeprocess",
        )
        self.assertEqual(authorized.pk, self.transition.pk)

    def test_execution_revalidates_version_and_rolls_back_denied_call(self):
        with self.assertRaises(TransitionVersionConflict):
            authorize_transition_execution(
                user=self.user, transition_id=self.transition.pk, current_stage_id=self.source.pk,
                expected_workflow_version_id=999, process_status=ProcessStatus.IN_PROGRESS,
                permission="processes.forward_administrativeprocess",
            )
        self.membership.active = False
        self.membership.is_primary = False
        self.membership.save()
        with self.assertRaises(TransitionDenied):
            authorize_transition_execution(
                user=self.user, transition_id=self.transition.pk, current_stage_id=self.source.pk,
                expected_workflow_version_id=self.workflow.current_version_id,
                process_status=ProcessStatus.IN_PROGRESS, permission="processes.forward_administrativeprocess",
            )
        self.transition.refresh_from_db()
        self.assertTrue(self.transition.active)
