from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AuthenticationApiTests(APITestCase):
    def setUp(self):
        self.admin_group = Group.objects.get(name="Administrador")
        self.user_group = Group.objects.get(name="Usuário")
        self.admin = get_user_model().objects.create_user(
            username="admin_test", password="safe-test-password", email="admin@example.com", is_staff=True
        )
        self.admin.groups.add(self.admin_group)

    def login(self):
        response = self.client.post(reverse("auth-login"), {"username": "admin_test", "password": "safe-test-password"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("password", response.data["user"])
        return response.data

    def test_login_me_dashboard_and_logout(self):
        tokens = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)
        dashboard = self.client.get(reverse("core:dashboard"))
        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertIn("total_users", dashboard.data)
        self.assertEqual(self.client.post(reverse("auth-logout"), {"refresh": tokens["refresh"]}).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self.client.post(reverse("auth-refresh"), {"refresh": tokens["refresh"]}).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_refresh_rotates_token_and_protected_endpoints_require_authentication(self):
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, status.HTTP_401_UNAUTHORIZED)

        tokens = self.login()
        refreshed = self.client.post(reverse("auth-refresh"), {"refresh": tokens["refresh"]})
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access", refreshed.data)
        self.assertIn("refresh", refreshed.data)
        self.assertNotEqual(refreshed.data["refresh"], tokens["refresh"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
        profile = self.client.get(reverse("auth-me"))
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertIn("groups", profile.data)
        self.assertIn("permissions", profile.data)

    def test_administrator_can_create_and_search_users_without_password_leak(self):
        tokens = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        created = self.client.post(reverse("user-list"), {
            "username": "new_user", "password": "another-safe-password", "first_name": "New",
            "last_name": "User", "email": "new@example.com", "group_names": ["Usuário"], "is_active": True,
        })
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", created.data)
        listed = self.client.get(reverse("user-list"), {"search": "new_user", "ordering": "username"})
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["count"], 1)

    def test_regular_user_cannot_access_administration(self):
        user = get_user_model().objects.create_user(username="regular", password="safe-test-password")
        user.groups.add(self.user_group)
        login = self.client.post(reverse("auth-login"), {"username": "regular", "password": "safe-test-password"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(self.client.get(reverse("user-list")).status_code, status.HTTP_403_FORBIDDEN)
