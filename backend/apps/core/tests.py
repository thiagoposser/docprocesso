from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from django.core.exceptions import ValidationError

from .models import SystemSettings


class SystemSettingsApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(username="settings_admin", password="safe-password", is_staff=True)
        self.user = users.objects.create_user(username="settings_user", password="safe-password")
        self.user.groups.add(Group.objects.get(name="Usuário"))
        self.settings = SystemSettings.load()

    def test_public_endpoint_has_only_allowlisted_fields(self):
        response = self.client.get(reverse("core:settings-public"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), {"system_name", "system_short_name", "logo_url", "primary_color", "language_code", "timezone", "version"})
        self.assertNotIn("maintenance_mode", response.data)
        self.assertNotIn("support_email", response.data)

    def test_only_administrator_reads_and_updates_admin_settings(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(reverse("core:settings-admin")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(reverse("core:settings-admin"), {"system_name": "Negado"}).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(reverse("core:settings-admin"), {"system_name": "Novo Sistema", "primary_color": "#123ABC"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.system_name, "Novo Sistema")
        self.assertEqual(self.settings.primary_color, "#123abc")

    def test_maintenance_blocks_regular_user_but_not_admin_or_login(self):
        self.settings.maintenance_mode = True
        self.settings.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.json()["code"], "maintenance_mode")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.admin)}")
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, status.HTTP_200_OK)
        self.client.credentials()
        self.assertNotEqual(self.client.post(reverse("auth-login"), {"username": "invalid", "password": "invalid"}).status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_singleton_cannot_be_duplicated(self):
        second = SystemSettings(system_name="Outro")
        with self.assertRaises(ValidationError):
            second.save()
        self.assertEqual(SystemSettings.objects.count(), 1)
