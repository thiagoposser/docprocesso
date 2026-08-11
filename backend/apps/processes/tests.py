from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.sectors.models import Sector

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
