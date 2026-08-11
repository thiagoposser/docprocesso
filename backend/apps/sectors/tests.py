from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from .models import Sector


class SectorModelTests(TestCase):
    def test_supports_flexible_hierarchy_and_optional_manager(self):
        manager = get_user_model().objects.create_user(username="sector_manager")
        organization = Sector.objects.create(name="Organização", code="ORG", manager=manager)
        directorate = Sector.objects.create(name="Diretoria", code="DIR", parent=organization)
        team = Sector.objects.create(name="Setor", parent=directorate)

        self.assertEqual(team.parent, directorate)
        self.assertEqual(directorate.parent, organization)
        self.assertEqual(organization.manager, manager)
        self.assertIsNone(team.code)

    def test_rejects_direct_and_indirect_cycles(self):
        root = Sector.objects.create(name="Raiz")
        child = Sector.objects.create(name="Filho", parent=root)
        grandchild = Sector.objects.create(name="Neto", parent=child)

        root.parent = root
        with self.assertRaisesMessage(ValidationError, "não pode ser pai de si mesmo"):
            root.save()

        root.parent = grandchild
        with self.assertRaisesMessage(ValidationError, "não pode conter ciclos"):
            root.save()

    def test_code_is_unique_but_optional(self):
        Sector.objects.create(name="Sem código 1")
        Sector.objects.create(name="Sem código 2", code="")
        Sector.objects.create(name="Com código", code="FIN")

        with self.assertRaises(ValidationError):
            Sector.objects.create(name="Código repetido", code="FIN")

    def test_inactivation_preserves_sector_and_hierarchy(self):
        parent = Sector.objects.create(name="Ativo")
        child = Sector.objects.create(name="Histórico", parent=parent)

        child.active = False
        child.save()

        self.assertTrue(Sector.objects.filter(pk=child.pk, active=False).exists())
        self.assertEqual(parent.children.get(), child)

    def test_parent_and_manager_are_protected_from_deletion(self):
        manager = get_user_model().objects.create_user(username="protected_manager")
        parent = Sector.objects.create(name="Pai", manager=manager)
        Sector.objects.create(name="Filho", parent=parent)

        with self.assertRaises(ProtectedError):
            parent.delete()
        with self.assertRaises(ProtectedError):
            manager.delete()

    def test_declares_expected_permissions_without_delete(self):
        self.assertEqual(Sector._meta.default_permissions, ("add", "change", "view"))
        self.assertIn(("manage_sector", "Pode gerenciar setores"), Sector._meta.permissions)
