from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sectors.models import OrganizationalFunction, Sector, UserSectorMembership

from .models import AdministrativeProcess, ProcessEventType, ProcessStatus, ProcessType, WorkflowStage
from .workflow_services import create_workflow


class ProcessAssignmentApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username="assign_manager", first_name="Gestora")
        self.candidate = User.objects.create_user(username="eligible_user", first_name="Ana", last_name="Silva")
        self.wrong_function = User.objects.create_user(username="wrong_function")
        self.expired = User.objects.create_user(username="expired_user")
        self.other = User.objects.create_user(username="other_sector")
        self.unlinked_manager = User.objects.create_user(username="unlinked_manager")
        self.sector = Sector.objects.create(name="Financeiro assignment", code="ASG-FIN")
        self.other_sector = Sector.objects.create(name="Outro assignment", code="ASG-OUT")
        self.function = OrganizationalFunction.objects.create(name="Analista assignment", code="ASG-AN")
        self.other_function = OrganizationalFunction.objects.create(name="Outra assignment", code="ASG-OT")
        UserSectorMembership.objects.create(user=self.manager, sector=self.sector, is_primary=True)
        UserSectorMembership.objects.create(user=self.candidate, sector=self.sector, function=self.function, is_primary=True)
        UserSectorMembership.objects.create(user=self.wrong_function, sector=self.sector, function=self.other_function, is_primary=True)
        UserSectorMembership.objects.create(
            user=self.expired, sector=self.sector, function=self.function, is_primary=True,
            starts_on=timezone.localdate() - timedelta(days=2),
            ends_on=timezone.localdate() - timedelta(days=1),
        )
        UserSectorMembership.objects.create(user=self.other, sector=self.other_sector, is_primary=True)
        view_permission = Permission.objects.get(codename="view_administrativeprocess")
        for user in (self.manager, self.candidate, self.wrong_function, self.expired, self.other):
            user.user_permissions.add(view_permission)
        self.manager.user_permissions.add(Permission.objects.get(codename="assign_administrativeprocess"))
        self.other.user_permissions.add(Permission.objects.get(codename="assign_administrativeprocess"))
        self.unlinked_manager.user_permissions.add(view_permission, Permission.objects.get(codename="assign_administrativeprocess"))
        workflow = create_workflow(code="assignment-flow", name="Assignment")
        stage = WorkflowStage.objects.create(
            workflow_version=workflow.current_version, order=1, name="Análise", is_initial=True,
            responsible_sector=self.sector, responsible_function=self.function,
        )
        process_type = ProcessType.objects.create(name="Assignment", code="assignment", workflow=workflow)
        self.process = AdministrativeProcess.objects.create(
            title="Atribuir", process_type=process_type, created_by=self.manager,
            origin_sector=self.sector, current_sector=self.sector, status=ProcessStatus.OPEN,
            workflow_version=workflow.current_version, current_stage=stage,
            responsible_sector=self.sector, responsible_function=self.function,
        )
        self.client.force_authenticate(self.manager)

    def test_lists_only_effective_eligible_users_and_searches_by_name(self):
        url = reverse("process-eligible-assignees", args=[self.process.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [self.candidate.pk])
        self.assertEqual(self.client.get(url, {"search": "Ana"}).data[0]["name"], "Ana Silva")
        self.assertEqual(self.client.get(url, {"search": "inexistente"}).data, [])

    def test_assigns_atomically_records_history_and_rejects_stale_or_ineligible(self):
        url = reverse("process-assign", args=[self.process.pk])
        assigned = self.client.post(url, {"assignee": self.candidate.pk, "version": 1}, format="json")
        self.assertEqual(assigned.status_code, status.HTTP_200_OK)
        self.assertEqual(assigned.data["assignee"], self.candidate.pk)
        event = self.process.events.get(event_type=ProcessEventType.ASSIGNMENT_CHANGED)
        self.assertEqual(event.payload["previous_assignee_id"], None)
        self.assertEqual(event.payload["assignee_id"], self.candidate.pk)
        stale = self.client.post(url, {"assignee": self.candidate.pk, "version": 1}, format="json")
        self.assertEqual(stale.status_code, status.HTTP_409_CONFLICT)
        invalid = self.client.post(url, {"assignee": self.wrong_function.pk, "version": 2}, format="json")
        self.assertEqual(invalid.status_code, status.HTTP_403_FORBIDDEN)
        self.process.refresh_from_db()
        self.assertEqual(self.process.assignee, self.candidate)
        self.assertEqual(self.process.events.filter(event_type=ProcessEventType.ASSIGNMENT_CHANGED).count(), 1)

    def test_assignment_cannot_be_forced_from_another_sector_or_without_membership(self):
        url = reverse("process-assign", args=[self.process.pk])
        for actor in (self.other, self.unlinked_manager):
            with self.subTest(actor=actor.username):
                self.client.force_authenticate(actor)
                response = self.client.post(url, {"assignee": self.candidate.pk, "version": 1}, format="json")
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.process.refresh_from_db()
                self.assertIsNone(self.process.assignee_id)
                self.assertFalse(self.process.events.filter(event_type=ProcessEventType.ASSIGNMENT_CHANGED).exists())
