from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sectors.models import Sector, UserSectorMembership

from .models import AdministrativeProcess, ProcessMovement, ProcessMovementAction, ProcessStatus, ProcessType


class AdministrativeProcessModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="process_author")
        self.sector = Sector.objects.create(name="Protocolo", code="PROTO")
        self.process_type = ProcessType.objects.create(name="Administrativo", code="administrativo")

    def make_process(self, **changes):
        values = {
            "title": "Aquisição de material",
            "process_type": self.process_type,
            "created_by": self.user,
            "origin_sector": self.sector,
        }
        values.update(changes)
        return AdministrativeProcess.objects.create(**values)

    def test_creates_consistent_draft_with_unique_opaque_number(self):
        first = self.make_process()
        second = self.make_process(title="Segundo processo")

        self.assertEqual(first.status, ProcessStatus.DRAFT)
        self.assertEqual(first.version, 1)
        self.assertIsNone(first.current_sector)
        self.assertTrue(first.number.startswith("DP-"))
        self.assertNotEqual(first.number, second.number)

    def test_requires_current_sector_outside_draft(self):
        with self.assertRaisesMessage(ValidationError, "setor atual é obrigatório"):
            self.make_process(status=ProcessStatus.OPEN, opened_at=timezone.now())

    def test_requires_dates_for_terminal_states(self):
        with self.assertRaisesMessage(ValidationError, "data de conclusão é obrigatória"):
            self.make_process(status=ProcessStatus.COMPLETED, current_sector=self.sector)
        with self.assertRaisesMessage(ValidationError, "data de arquivamento é obrigatória"):
            self.make_process(status=ProcessStatus.ARCHIVED, current_sector=self.sector)

    def test_generic_save_does_not_apply_lifecycle_side_effects(self):
        process = self.make_process(current_sector=self.sector)
        process.status = ProcessStatus.OPEN
        process.save()

        self.assertIsNone(process.opened_at)
        self.assertEqual(process.version, 1)

    def test_rejects_invalid_version(self):
        with self.assertRaisesMessage(ValidationError, "versão deve ser maior"):
            self.make_process(version=0)

    def test_referenced_records_are_protected(self):
        self.make_process(current_sector=self.sector, assignee=self.user)

        for referenced in (self.process_type, self.sector, self.user):
            with self.assertRaises(ProtectedError):
                referenced.delete()

    def test_declares_action_permissions_and_no_delete_permission(self):
        self.assertEqual(AdministrativeProcess._meta.default_permissions, ("add", "change", "view"))
        codenames = {codename for codename, _ in AdministrativeProcess._meta.permissions}
        self.assertEqual(
            codenames,
            {
                "open_administrativeprocess",
                "forward_administrativeprocess",
                "receive_administrativeprocess",
                "return_administrativeprocess",
                "complete_administrativeprocess",
                "reopen_administrativeprocess",
                "cancel_administrativeprocess",
                "archive_administrativeprocess",
            },
        )


class AdministrativeProcessApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="process_api_user")
        self.other = users.objects.create_user(username="process_api_other")
        self.sector = Sector.objects.create(name="API Protocolo", code="API-PROTO")
        self.other_sector = Sector.objects.create(name="API Restrito", code="API-REST")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        UserSectorMembership.objects.create(user=self.other, sector=self.other_sector, is_primary=True)
        self.process_type = ProcessType.objects.create(name="API Administrativo", code="api-administrativo")
        permissions = Permission.objects.filter(
            codename__in=["view_administrativeprocess", "add_administrativeprocess", "change_administrativeprocess"]
        )
        self.user.user_permissions.add(*permissions)
        self.other.user_permissions.add(*permissions)
        self.client.force_authenticate(self.user)

    def create_process(self, *, user=None, sector=None, **changes):
        values = {
            "title": "Processo visível",
            "process_type": self.process_type,
            "created_by": user or self.user,
            "origin_sector": sector or self.sector,
        }
        values.update(changes)
        return AdministrativeProcess.objects.create(**values)

    def test_creates_lists_retrieves_and_edits_draft(self):
        created = self.client.post(
            reverse("process-list"),
            {"title": "Compra", "description": "Material", "process_type": self.process_type.pk, "origin_sector": self.sector.pk},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["created_by"], self.user.pk)
        listed = self.client.get(reverse("process-list"))
        self.assertEqual(listed.data["count"], 1)
        detail = reverse("process-detail", args=[created.data["id"]])
        updated = self.client.patch(detail, {"title": "Compra atualizada"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["title"], "Compra atualizada")
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_isolates_queryset_and_returns_404_outside_sector_scope(self):
        visible = self.create_process()
        hidden = self.create_process(user=self.other, sector=self.other_sector, title="Sigiloso")

        response = self.client.get(reverse("process-list"), {"search": "Sigiloso"})
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(self.client.get(reverse("process-detail", args=[hidden.pk])).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse("process-detail", args=[visible.pk])).status_code, status.HTTP_200_OK)

    def test_rejects_creation_outside_scope_and_protected_patch_fields(self):
        denied = self.client.post(
            reverse("process-list"),
            {"title": "Negado", "process_type": self.process_type.pk, "origin_sector": self.other_sector.pk},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        process = self.create_process()
        response = self.client.patch(
            reverse("process-detail", args=[process.pk]),
            {"status": ProcessStatus.OPEN, "current_sector": self.other_sector.pk, "version": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)
        relocation = self.client.patch(
            reverse("process-detail", args=[process.pk]),
            {"origin_sector": self.other_sector.pk},
            format="json",
        )
        self.assertEqual(relocation.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("origin_sector", relocation.data)

    def test_requires_permissions_and_membership_for_reading(self):
        unprivileged = get_user_model().objects.create_user(username="process_unprivileged")
        UserSectorMembership.objects.create(user=unprivileged, sector=self.sector)
        self.client.force_authenticate(unprivileged)
        self.assertEqual(self.client.get(reverse("process-list")).status_code, status.HTTP_403_FORBIDDEN)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("process-list")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filters_only_within_scope_and_validates_parameters(self):
        first = self.create_process(title="Contrato alfa", assignee=self.user)
        self.create_process(title="Outro", status=ProcessStatus.OPEN, current_sector=self.sector)

        response = self.client.get(
            reverse("process-list"),
            {"number": first.number[3:10], "type": self.process_type.pk, "status": ProcessStatus.DRAFT, "sector": self.sector.pk, "assignee": self.user.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.client.get(reverse("process-list"), {"created_from": "invalid"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(reverse("process-list"), {"status": "UNKNOWN"}).status_code, status.HTTP_400_BAD_REQUEST)

    def test_lists_only_active_process_types(self):
        ProcessType.objects.create(name="Inativo", code="inativo", active=False)
        response = self.client.get(reverse("process-type-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [self.process_type.pk])


class ProcessMovementModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="movement_actor")
        self.origin = Sector.objects.create(name="Movimento origem", code="MOV-O")
        self.destination = Sector.objects.create(name="Movimento destino", code="MOV-D")
        process_type = ProcessType.objects.create(name="Movimentação", code="movimentacao")
        self.process = AdministrativeProcess.objects.create(
            title="Processo movimentado",
            process_type=process_type,
            created_by=self.user,
            origin_sector=self.origin,
        )

    def movement(self, **changes):
        values = {
            "process": self.process,
            "action": ProcessMovementAction.OPEN,
            "from_sector": None,
            "to_sector": self.origin,
            "actor": self.user,
            "status_before": ProcessStatus.DRAFT,
            "status_after": ProcessStatus.OPEN,
        }
        values.update(changes)
        return ProcessMovement.objects.create(**values)

    def test_records_ordered_append_only_history(self):
        first = self.movement()
        second = self.movement(
            action=ProcessMovementAction.FORWARD,
            from_sector=self.origin,
            to_sector=self.destination,
            status_before=ProcessStatus.OPEN,
            status_after=ProcessStatus.IN_PROGRESS,
        )

        self.assertEqual(list(ProcessMovement.objects.for_process(self.process)), [first, second])
        self.assertEqual(ProcessMovement._meta.default_permissions, ("view",))

    def test_rejects_instance_and_queryset_mutation(self):
        movement = self.movement()
        movement.note = "alterado"
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            movement.save()
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            ProcessMovement.objects.filter(pk=movement.pk).update(note="alterado")
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            movement.delete()
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            ProcessMovement.objects.filter(pk=movement.pk).delete()

    def test_requires_note_for_return_cancel_and_reopen(self):
        for action in (ProcessMovementAction.RETURN, ProcessMovementAction.CANCEL, ProcessMovementAction.REOPEN):
            values = {"action": action, "from_sector": self.origin, "to_sector": self.destination}
            if action in {ProcessMovementAction.CANCEL, ProcessMovementAction.REOPEN}:
                values["to_sector"] = self.origin
            with self.assertRaisesMessage(ValidationError, "observação é obrigatória"):
                self.movement(**values)

    def test_enforces_sector_coherence_by_action(self):
        with self.assertRaisesMessage(ValidationError, "somente o setor de destino"):
            self.movement(from_sector=self.origin)
        with self.assertRaisesMessage(ValidationError, "origem e destino diferentes"):
            self.movement(action=ProcessMovementAction.FORWARD, from_sector=self.origin, to_sector=self.origin)
        with self.assertRaisesMessage(ValidationError, "permanecer no mesmo setor"):
            self.movement(action=ProcessMovementAction.RECEIVE, from_sector=self.origin, to_sector=self.destination)
        with self.assertRaisesMessage(ValidationError, "ação de estado"):
            self.movement(action=ProcessMovementAction.COMPLETE, from_sector=None, to_sector=None)

    def test_referenced_records_are_protected(self):
        self.movement()
        for referenced in (self.process, self.origin, self.user):
            with self.assertRaises(ProtectedError):
                referenced.delete()

    def test_declares_expected_indexes(self):
        names = {index.name for index in ProcessMovement._meta.indexes}
        self.assertEqual(names, {"movement_process_date_idx", "movement_from_date_idx", "movement_to_date_idx", "movement_action_date_idx"})
