from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.core.models import SystemSettings

from .membership_services import save_membership
from .models import OrganizationalFunction, OrganizationalUnit, Sector, UserSectorMembership
from .policies import evaluate_sector_access


class OrganizationalFunctionTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.reader = users.objects.create_user(username="function_reader")
        self.manager = users.objects.create_user(username="function_manager")
        self.manager.user_permissions.add(Permission.objects.get(codename="manage_organizational_function"))
        self.active = OrganizationalFunction.objects.create(name="Gerente", code=" manager ")
        self.inactive = OrganizationalFunction.objects.create(name="Histórica", code="HISTORY", active=False)

    def test_code_is_normalized_unique_and_not_a_fixed_enum(self):
        self.assertEqual(self.active.code, "MANAGER")
        with self.assertRaises(ValidationError):
            OrganizationalFunction.objects.create(name="Duplicada", code="manager")
        self.assertFalse(hasattr(OrganizationalFunction, "FunctionChoices"))

    def test_reader_only_sees_active_and_cannot_write(self):
        self.client.force_authenticate(self.reader)
        response = self.client.get(reverse("organizational-function-list"))
        self.assertEqual([item["id"] for item in response.data["results"]], [self.active.pk])
        self.assertEqual(self.client.post(reverse("organizational-function-list"), {"name": "Analista", "code": "ANALYST"}).status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_creates_edits_inactivates_filters_and_cannot_delete(self):
        self.client.force_authenticate(self.manager)
        created = self.client.post(reverse("organizational-function-list"), {"name": "Analista", "code": "analyst", "description": "Análise"}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["code"], "ANALYST")
        detail = reverse("organizational-function-detail", args=[created.data["id"]])
        self.assertEqual(self.client.patch(detail, {"active": False}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("organizational-function-list"), {"active": "false"}).data["count"], 2)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_access_is_rejected_and_groups_are_unchanged(self):
        from django.contrib.auth.models import Group
        before = list(Group.objects.values_list("id", "name"))
        self.assertEqual(self.client.get(reverse("organizational-function-list")).status_code, status.HTTP_401_UNAUTHORIZED)
        OrganizationalFunction.objects.create(name="Assistente", code="ASSISTANT")
        self.assertEqual(list(Group.objects.values_list("id", "name")), before)


class OrganizationalUnitModelTests(TestCase):
    def test_supports_hierarchy_normalizes_acronym_and_prevents_cycles(self):
        root = OrganizationalUnit.objects.create(name="Administração", acronym=" adm ")
        child = OrganizationalUnit.objects.create(name="Regional", acronym="REG", parent=root)

        self.assertEqual(root.acronym, "ADM")
        root.parent = child
        with self.assertRaisesMessage(ValidationError, "hierarquia de unidades"):
            root.save()

    def test_protects_parent_with_children_from_deletion(self):
        root = OrganizationalUnit.objects.create(name="Administração", acronym="ADM")
        OrganizationalUnit.objects.create(name="Regional", acronym="REG", parent=root)

        with self.assertRaises(ProtectedError):
            root.delete()


class OrganizationalUnitApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="unit_reader")
        self.manager = users.objects.create_user(username="unit_manager")
        self.manager.user_permissions.add(Permission.objects.get(codename="manage_organizational_unit"))
        self.root = OrganizationalUnit.objects.create(name="Administração", acronym="ADM")
        self.child = OrganizationalUnit.objects.create(name="Regional", acronym="REG", parent=self.root)
        self.inactive = OrganizationalUnit.objects.create(name="Histórica", acronym="HIST", active=False)

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def test_authenticated_reader_only_lists_active_units(self):
        self.authenticate(self.user)

        response = self.client.get(reverse("organizational-unit-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["acronym"] for item in response.data["results"]}, {"ADM", "REG"})
        self.assertEqual(
            self.client.get(reverse("organizational-unit-detail", args=[self.inactive.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_manager_can_create_update_filter_and_cannot_delete(self):
        self.authenticate(self.manager)

        created = self.client.post(
            reverse("organizational-unit-list"),
            {"name": "Tecnologia", "acronym": "ti", "description": "Unidade de TI", "parent": self.root.pk},
            format="json",
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["acronym"], "TI")
        detail = reverse("organizational-unit-detail", args=[created.data["id"]])
        self.assertEqual(self.client.patch(detail, {"name": "Tecnologia da Informação"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("organizational-unit-list"), {"active": "false"}).data["count"], 1)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_rejects_inactive_parent_cycle_and_parent_inactivation(self):
        self.authenticate(self.manager)
        inactive_parent = self.client.post(
            reverse("organizational-unit-list"),
            {"name": "Inválida", "acronym": "INV", "parent": self.inactive.pk},
            format="json",
        )
        self.assertEqual(inactive_parent.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", inactive_parent.data)

        cycle = self.client.patch(
            reverse("organizational-unit-detail", args=[self.root.pk]),
            {"parent": self.child.pk},
            format="json",
        )
        self.assertEqual(cycle.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", cycle.data)

        inactivation = self.client.patch(
            reverse("organizational-unit-detail", args=[self.root.pk]),
            {"active": False},
            format="json",
        )
        self.assertEqual(inactivation.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active", inactivation.data)

    def test_write_requires_permission_and_authentication_is_mandatory(self):
        self.authenticate(self.user)
        self.assertEqual(
            self.client.post(reverse("organizational-unit-list"), {"name": "TI", "acronym": "TI"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(reverse("organizational-unit-list")).status_code, status.HTTP_401_UNAUTHORIZED)


class SectorModelTests(TestCase):
    def test_rejects_parent_from_another_unit_when_both_are_defined(self):
        first = OrganizationalUnit.objects.create(name="Primeira", acronym="FIRST")
        second = OrganizationalUnit.objects.create(name="Segunda", acronym="SECOND")
        parent = Sector.objects.create(name="Pai", unit=first)

        with self.assertRaisesMessage(ValidationError, "mesma unidade"):
            Sector.objects.create(name="Filho", unit=second, parent=parent)

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
        self.unit = OrganizationalUnit.objects.create(name="Administração", acronym="ADM")
        self.other_unit = OrganizationalUnit.objects.create(name="Regional", acronym="REG")
        self.inactive_unit = OrganizationalUnit.objects.create(name="Histórica", acronym="HIST", active=False)
        self.root = Sector.objects.create(name="Organização", code="ORG", unit=self.unit, manager=self.manager)
        self.active_child = Sector.objects.create(name="Financeiro", code="FIN", unit=self.unit, parent=self.root)
        self.inactive = Sector.objects.create(name="Arquivo", code="ARQ", unit=self.unit, active=False)

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def test_authenticated_user_lists_only_active_sectors_and_filters(self):
        self.authenticate(self.user)
        response = self.client.get(reverse("sector-list"), {"search": "Financeiro", "parent": self.root.pk, "ordering": "name"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.active_child.pk)
        self.assertEqual(response.data["results"][0]["unit_name"], self.unit.name)
        self.assertNotContains(self.client.get(reverse("sector-list")), "Arquivo")
        self.assertEqual(self.client.get(reverse("sector-list"), {"unit": self.other_unit.pk}).data["count"], 0)

    def test_tree_is_ordered_nested_and_uses_a_bounded_query_count(self):
        self.authenticate(self.manager)
        Sector.objects.create(name="Administrativo", code="ADM", unit=self.unit, parent=self.root)
        SystemSettings.load()

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
        created = self.client.post(reverse("sector-list"), {"name": "TI", "code": "TI", "unit": self.unit.pk, "parent": self.root.pk}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        detail = reverse("sector-detail", args=[created.data["id"]])
        self.assertEqual(self.client.patch(detail, {"name": "Tecnologia"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_rejects_inactive_parent_cycle_and_invalid_inactivation(self):
        self.authenticate(self.manager)
        inactive_parent = self.client.post(reverse("sector-list"), {"name": "Inválido", "unit": self.unit.pk, "parent": self.inactive.pk}, format="json")
        self.assertEqual(inactive_parent.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", inactive_parent.data)

        cycle = self.client.patch(reverse("sector-detail", args=[self.root.pk]), {"parent": self.active_child.pk}, format="json")
        self.assertEqual(cycle.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", cycle.data)

        inactivation = self.client.patch(reverse("sector-detail", args=[self.root.pk]), {"active": False}, format="json")
        self.assertEqual(inactivation.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active", inactivation.data)

    def test_new_sector_requires_active_unit_and_compatible_parent(self):
        self.authenticate(self.manager)
        missing = self.client.post(reverse("sector-list"), {"name": "Sem unidade"}, format="json")
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unit", missing.data)

        inactive = self.client.post(
            reverse("sector-list"),
            {"name": "Unidade inativa", "unit": self.inactive_unit.pk},
            format="json",
        )
        self.assertEqual(inactive.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unit", inactive.data)

        incompatible = self.client.post(
            reverse("sector-list"),
            {"name": "Outro setor", "unit": self.other_unit.pk, "parent": self.root.pk},
            format="json",
        )
        self.assertEqual(incompatible.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", incompatible.data)

    def test_manager_can_filter_inactive_and_invalid_parent_filter_is_clear(self):
        self.authenticate(self.manager)
        response = self.client.get(reverse("sector-list"), {"active": "false"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.inactive.pk)
        invalid = self.client.get(reverse("sector-list"), {"parent": "invalid"})
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", invalid.data)

    def test_edit_preserves_an_existing_inactive_parent_without_allowing_reallocation(self):
        child = Sector.objects.create(name="Filho histórico", parent=self.root)
        child.active = False
        child.save()
        self.root.active = False
        self.root.save()
        self.authenticate(self.manager)

        detail = reverse("sector-detail", args=[child.pk])
        updated = self.client.patch(detail, {"name": "Filho preservado", "parent": self.root.pk}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        rejected = self.client.patch(reverse("sector-detail", args=[self.inactive.pk]), {"parent": self.root.pk}, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_authentication_for_reading(self):
        self.assertEqual(self.client.get(reverse("sector-list")).status_code, status.HTTP_401_UNAUTHORIZED)


class UserSectorMembershipTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="member_user")
        self.other_user = users.objects.create_user(username="other_member")
        self.first = Sector.objects.create(name="Primeiro", code="FIRST")
        self.second = Sector.objects.create(name="Segundo", code="SECOND")

    def test_user_can_belong_to_multiple_sectors_with_one_active_primary(self):
        primary = UserSectorMembership.objects.create(user=self.user, sector=self.first, is_primary=True)
        secondary = UserSectorMembership.objects.create(user=self.user, sector=self.second, is_manager=True)

        self.assertTrue(primary.is_primary)
        self.assertFalse(secondary.is_primary)
        self.assertTrue(secondary.is_manager)
        secondary.is_primary = True
        with self.assertRaises(ValidationError):
            secondary.save()

    def test_service_changes_primary_without_losing_membership_history(self):
        old = UserSectorMembership.objects.create(user=self.user, sector=self.first, is_primary=True)
        new = UserSectorMembership.objects.create(user=self.user, sector=self.second)

        save_membership(new, is_primary=True)
        old.refresh_from_db()

        self.assertFalse(old.is_primary)
        self.assertTrue(new.is_primary)
        self.assertEqual(UserSectorMembership.objects.count(), 2)

    def test_primary_must_be_active_and_user_sector_pair_is_unique(self):
        UserSectorMembership.objects.create(user=self.user, sector=self.first)
        with self.assertRaises(ValidationError):
            UserSectorMembership.objects.create(user=self.user, sector=self.first)
        with self.assertRaises(ValidationError):
            UserSectorMembership.objects.create(user=self.user, sector=self.second, active=False, is_primary=True)

    def test_inactive_user_or_sector_cannot_receive_active_membership(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.assertRaisesMessage(ValidationError, "usuário inativo"):
            UserSectorMembership.objects.create(user=self.user, sector=self.first)

        self.second.active = False
        self.second.save()
        with self.assertRaisesMessage(ValidationError, "setor inativo"):
            UserSectorMembership.objects.create(user=self.other_user, sector=self.second)

    def test_inactivation_preserves_membership_and_allows_legacy_users_without_one(self):
        membership = UserSectorMembership.objects.create(user=self.user, sector=self.first)
        membership.active = False
        membership.save()

        self.assertTrue(UserSectorMembership.objects.filter(pk=membership.pk, active=False).exists())
        self.assertFalse(self.other_user.sector_memberships.exists())

    def test_inactive_historical_membership_can_be_edited_but_not_reactivated_with_inactive_references(self):
        membership = UserSectorMembership.objects.create(user=self.user, sector=self.first)
        membership.active = False
        membership.save()
        self.first.active = False
        self.first.save()

        membership.is_manager = True
        membership.save()
        membership.active = True
        with self.assertRaisesMessage(ValidationError, "setor inativo"):
            membership.save()

    def test_current_user_response_adds_only_active_memberships(self):
        UserSectorMembership.objects.create(user=self.user, sector=self.first, is_primary=True)
        UserSectorMembership.objects.create(user=self.user, sector=self.second, active=False)
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["sector_memberships"]), 1)
        self.assertEqual(response.data["sector_memberships"][0]["sector"], self.first.pk)


class UserSectorMembershipApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(username="membership_admin", is_staff=True)
        self.user = users.objects.create_user(username="membership_user")
        self.other = users.objects.create_user(username="membership_other")
        self.first = Sector.objects.create(name="API Primeiro", code="API1")
        self.second = Sector.objects.create(name="API Segundo", code="API2")
        self.mine = UserSectorMembership.objects.create(user=self.user, sector=self.first, is_primary=True)
        self.theirs = UserSectorMembership.objects.create(user=self.other, sector=self.second)

    def test_regular_user_only_reads_own_active_memberships(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("user-sector-membership-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.mine.pk])
        self.assertEqual(self.client.get(reverse("user-sector-membership-detail", args=[self.theirs.pk])).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(reverse("user-sector-membership-list"), {}).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_creates_filters_updates_and_cannot_delete_membership(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(reverse("user-sector-membership-list"), {"user": self.user.pk, "sector": self.second.pk, "active": True, "is_primary": True, "is_manager": True}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.mine.refresh_from_db()
        self.assertFalse(self.mine.is_primary)
        listed = self.client.get(reverse("user-sector-membership-list"), {"user": self.user.pk, "active": "true"})
        self.assertEqual(listed.data["count"], 2)
        detail = reverse("user-sector-membership-detail", args=[created.data["id"]])
        self.assertEqual(self.client.patch(detail, {"active": False, "is_primary": False}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_access_is_rejected(self):
        self.assertEqual(self.client.get(reverse("user-sector-membership-list")).status_code, status.HTTP_401_UNAUTHORIZED)


class SectorAccessPolicyTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="policy_user")
        self.superuser = users.objects.create_superuser(username="policy_root", password="safe-password")
        self.sector = Sector.objects.create(name="Política", code="POL")
        self.permission = Permission.objects.get(codename="manage_sector")

    def test_denies_by_default_and_requires_permission_plus_membership(self):
        decision = evaluate_sector_access(self.user, permission="sectors.manage_sector", sector=self.sector)
        self.assertEqual((decision.allowed, decision.reason), (False, "permission_required"))
        self.user.user_permissions.add(self.permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        decision = evaluate_sector_access(self.user, permission="sectors.manage_sector", sector=self.sector)
        self.assertEqual(decision.reason, "sector_membership_required")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector)
        self.assertTrue(evaluate_sector_access(self.user, permission="sectors.manage_sector", sector=self.sector).allowed)

    def test_rejects_inactive_sector_invalid_state_and_missing_manager_scope(self):
        self.user.user_permissions.add(self.permission)
        membership = UserSectorMembership.objects.create(user=self.user, sector=self.sector)
        self.assertEqual(evaluate_sector_access(self.user, permission="sectors.manage_sector", sector=self.sector, require_manager=True).reason, "sector_manager_required")
        membership.is_manager = True; membership.save()
        self.assertEqual(evaluate_sector_access(self.user, permission="sectors.manage_sector", sector=self.sector, resource_state="DONE", allowed_states={"OPEN"}).reason, "invalid_resource_state")
        self.sector.active = False; self.sector.save()
        self.assertEqual(evaluate_sector_access(self.user, permission="sectors.manage_sector", sector=self.sector).reason, "inactive_or_invalid_sector")

    def test_superuser_bypasses_scope_and_state(self):
        decision = evaluate_sector_access(self.superuser, permission="unknown.permission", sector=self.sector, resource_state="DONE", allowed_states={"OPEN"}, require_manager=True)
        self.assertEqual((decision.allowed, decision.reason), (True, "superuser"))
