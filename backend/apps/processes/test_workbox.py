from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sectors.models import OrganizationalFunction, OrganizationalUnit, Sector, UserSectorMembership

from .models import AdministrativeProcess, ProcessMovement, ProcessMovementAction, ProcessStatus, ProcessType, WorkflowStage, WorkflowTransition
from .workflow_services import create_workflow


class ProcessWorkboxTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workbox_user")
        self.other = get_user_model().objects.create_user(username="workbox_other")
        self.unit = OrganizationalUnit.objects.create(name="Unidade caixa", acronym="UCX")
        self.sector = Sector.objects.create(name="Caixa setor", code="BOX-S", unit=self.unit)
        self.other_sector = Sector.objects.create(name="Caixa outro", code="BOX-X")
        self.additional_sector = Sector.objects.create(name="Caixa adicional", code="BOX-A")
        self.function = OrganizationalFunction.objects.create(name="Analista caixa", code="BOX-F")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, function=self.function, is_primary=True)
        UserSectorMembership.objects.create(user=self.user, sector=self.additional_sector, is_manager=True)
        UserSectorMembership.objects.create(user=self.other, sector=self.other_sector, is_primary=True)
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=["view_administrativeprocess", "forward_administrativeprocess"]
        ))
        self.workflow = create_workflow(code="workbox", name="Caixa")
        self.source = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=1, name="Análise", is_initial=True,
            responsible_sector=self.sector, responsible_function=self.function,
        )
        self.target = WorkflowStage.objects.create(
            workflow_version=self.workflow.current_version, order=2, name="Final", is_final=True,
            responsible_sector=self.other_sector,
        )
        WorkflowTransition.objects.create(
            source_stage=self.source, destination_stage=self.target, code="enviar", name="Enviar",
            authorized_sector=self.sector, authorized_function=self.function,
        )
        WorkflowTransition.objects.create(
            source_stage=self.source, destination_stage=self.target, code="revisar", name="Revisar",
            authorized_sector=self.sector,
        )
        self.process_type = ProcessType.objects.create(name="Caixa", code="caixa", workflow=self.workflow)
        self.action_process = self.make_process("Ação", self.user, self.sector)
        ProcessMovement.objects.create(
            process=self.action_process, action=ProcessMovementAction.OPEN, actor=self.user,
            to_sector=self.sector, status_before=ProcessStatus.DRAFT, status_after=ProcessStatus.OPEN,
        )
        self.completed = self.make_process("Concluído", self.user, self.sector)
        AdministrativeProcess.objects.filter(pk=self.completed.pk).update(
            status=ProcessStatus.COMPLETED, completed_at=timezone.now()
        )
        self.hidden = self.make_process("Oculto", self.other, self.other_sector)
        self.client.force_authenticate(self.user)

    def make_process(self, title, creator, sector):
        return AdministrativeProcess.objects.create(
            title=title, process_type=self.process_type, workflow_version=self.workflow.current_version,
            current_stage=self.source, created_by=creator, origin_sector=sector, current_sector=sector,
            responsible_sector=sector, responsible_function=self.function, status=ProcessStatus.OPEN,
        )

    def get_scope(self, scope, **params):
        return self.client.get(reverse("process-workbox"), {"scope": scope, **params})

    def test_categories_are_scoped_paginated_and_distinct(self):
        my_action = self.get_scope("my-action")
        self.assertEqual(my_action.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in my_action.data["results"]], [self.action_process.pk])
        self.assertEqual(self.get_scope("my-sector").data["count"], 2)
        self.assertEqual(self.get_scope("created").data["count"], 2)
        self.assertEqual(self.get_scope("following").data["count"], 2)
        self.assertEqual([item["id"] for item in self.get_scope("completed").data["results"]], [self.completed.pk])
        for scope in ("my-action", "my-sector", "created", "following", "completed"):
            ids = [item["id"] for item in self.get_scope(scope).data["results"]]
            self.assertNotIn(self.hidden.pk, ids)

    def test_validates_scope_and_keeps_filters(self):
        self.assertEqual(self.get_scope("invalid").status_code, status.HTTP_400_BAD_REQUEST)
        filtered = self.get_scope("my-sector", search="Ação")
        self.assertEqual([item["id"] for item in filtered.data["results"]], [self.action_process.pk])
        for parameters in (
            {"unit": self.unit.pk}, {"stage": self.source.pk},
            {"responsible_sector": self.sector.pk}, {"responsible_function": self.function.pk},
        ):
            with self.subTest(parameters=parameters):
                response = self.get_scope("my-sector", **parameters)
                self.assertCountEqual(
                    [item["id"] for item in response.data["results"]],
                    [self.action_process.pk, self.completed.pk],
                )
        item = self.get_scope("my-action").data["results"][0]
        self.assertEqual(item["organizational_unit_name"], self.unit.name)
        self.assertEqual(item["created_by_name"], self.user.full_name)
        self.assertEqual(item["last_movement_action"], ProcessMovementAction.OPEN)
        self.assertEqual(item["last_movement_action_label"], ProcessMovementAction.OPEN.label)
        self.assertIsNotNone(item["last_movement_at"])

    def test_first_page_has_bounded_queries(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.get_scope("my-action")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(queries), 15)
