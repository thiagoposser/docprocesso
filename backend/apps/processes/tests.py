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

from .models import AdministrativeProcess, ProcessStatus, ProcessType


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
