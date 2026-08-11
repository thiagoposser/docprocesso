from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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


class SectorApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.manager = users.objects.create_user(username="api_manager", password="safe-password")
        self.manager.user_permissions.add(Permission.objects.get(codename="manage_sector"))
        self.user = users.objects.create_user(username="api_user", password="safe-password")
        self.root = Sector.objects.create(name="Organização", code="ORG", manager=self.manager)
        self.active_child = Sector.objects.create(name="Financeiro", code="FIN", parent=self.root)
        self.inactive = Sector.objects.create(name="Arquivo", code="ARQ", active=False)

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def test_authenticated_user_lists_only_active_sectors_and_filters(self):
        self.authenticate(self.user)
        response = self.client.get(reverse("sector-list"), {"search": "Financeiro", "parent": self.root.pk, "ordering": "name"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.active_child.pk)
        self.assertNotContains(self.client.get(reverse("sector-list")), "Arquivo")

    def test_tree_is_ordered_nested_and_uses_a_bounded_query_count(self):
        self.authenticate(self.manager)
        Sector.objects.create(name="Administrativo", code="ADM", parent=self.root)

        # Settings middleware (1), permission cache (2) and the complete tree (1).
        with self.assertNumQueries(4):
            response = self.client.get(reverse("sector-tree"), {"active": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["name"] for item in response.data], ["Organização"])
        self.assertEqual([item["name"] for item in response.data[0]["children"]], ["Administrativo", "Financeiro"])

    def test_manager_permission_controls_writes_and_delete_is_unavailable(self):
        self.authenticate(self.user)
        denied = self.client.post(reverse("sector-list"), {"name": "TI", "code": "TI"}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.manager)
        created = self.client.post(reverse("sector-list"), {"name": "TI", "code": "TI", "parent": self.root.pk}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        detail = reverse("sector-detail", args=[created.data["id"]])
        self.assertEqual(self.client.patch(detail, {"name": "Tecnologia"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_rejects_inactive_parent_cycle_and_invalid_inactivation(self):
        self.authenticate(self.manager)
        inactive_parent = self.client.post(reverse("sector-list"), {"name": "Inválido", "parent": self.inactive.pk}, format="json")
        self.assertEqual(inactive_parent.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", inactive_parent.data)

        cycle = self.client.patch(reverse("sector-detail", args=[self.root.pk]), {"parent": self.active_child.pk}, format="json")
        self.assertEqual(cycle.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", cycle.data)

        inactivation = self.client.patch(reverse("sector-detail", args=[self.root.pk]), {"active": False}, format="json")
        self.assertEqual(inactivation.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active", inactivation.data)

    def test_manager_can_filter_inactive_and_invalid_parent_filter_is_clear(self):
        self.authenticate(self.manager)
        response = self.client.get(reverse("sector-list"), {"active": "false"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.inactive.pk)
        invalid = self.client.get(reverse("sector-list"), {"parent": "invalid"})
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", invalid.data)

    def test_requires_authentication_for_reading(self):
        self.assertEqual(self.client.get(reverse("sector-list")).status_code, status.HTTP_401_UNAUTHORIZED)
