from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import SystemSettings
from apps.documents.models import Document, DocumentCategory
from .models import AuditAction, AuditLog
from .services import record_audit


class AuditApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(username="audit_admin", password="safe-password", is_staff=True)
        self.admin.groups.add(Group.objects.get(name="Administrador"))
        self.user = users.objects.create_user(username="audit_user", password="safe-password")
        self.category = DocumentCategory.objects.create(name="Auditoria")

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def test_user_document_and_settings_changes_are_audited_without_secrets(self):
        self.authenticate(self.admin)
        created = self.client.post(reverse("user-list"), {
            "username": "created_audit", "password": "never-log-this", "first_name": "Teste",
            "last_name": "Auditado", "email": "audit@example.com", "group_names": ["Usuário"], "is_active": True,
        }, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        user_log = AuditLog.objects.filter(action=AuditAction.CREATE, entity_type="users.User").latest("created_at")
        self.assertNotIn("password", str(user_log.new_values).lower())
        self.assertNotIn("never-log-this", str(user_log.new_values))

        document = self.client.post(reverse("document-list"), {"title": "Documento", "category": self.category.pk, "external_url": "https://example.com", "active": True}, format="json")
        self.assertEqual(document.status_code, status.HTTP_201_CREATED)
        changed = self.client.patch(reverse("document-detail", args=[document.data["id"]]), {"active": False}, format="json")
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.DEACTIVATE, entity_type="documents.Document").exists())

        settings = self.client.patch(reverse("core:settings-admin"), {"system_description": "Atualizado"}, format="json")
        self.assertEqual(settings.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.SETTINGS_CHANGED).exists())

    def test_login_logout_failed_login_view_and_download_are_audited(self):
        login = self.client.post(reverse("auth-login"), {"username": "audit_admin", "password": "safe-password"})
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.LOGIN, user=self.admin).exists())
        failed = self.client.post(reverse("auth-login"), {"username": "audit_admin", "password": "wrong-secret"})
        self.assertEqual(failed.status_code, status.HTTP_401_UNAUTHORIZED)
        failed_log = AuditLog.objects.filter(action=AuditAction.LOGIN_FAILED).latest("created_at")
        self.assertEqual(failed_log.new_values, {"username": "audit_admin"})
        self.assertNotIn("wrong-secret", str(failed_log.new_values))
        logout = self.client.post(reverse("auth-logout"), {"refresh": login.data["refresh"]})
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.LOGOUT, user=self.admin).exists())

    def test_api_requires_specific_permission_is_filtered_and_read_only(self):
        record_audit(action=AuditAction.UPDATE, description="Registro filtrável", user=self.admin, entity_type="users.User", entity_id="1")
        self.authenticate(self.user)
        self.assertEqual(self.client.get(reverse("audit-log-list")).status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.admin)
        response = self.client.get(reverse("audit-log-list"), {"action": "UPDATE", "entity": "users", "search": "filtrável", "method": "GET"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        response = self.client.get(reverse("audit-log-list"), {"action": "UPDATE", "entity": "users"})
        self.assertEqual(response.data["count"], 1)
        detail = reverse("audit-log-detail", args=[AuditLog.objects.get().pk])
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(reverse("audit-log-list"), {}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.patch(detail, {}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_sanitizer_removes_nested_sensitive_fields(self):
        log = record_audit(action=AuditAction.UPDATE, description="Seguro", new_values={"name": "ok", "password": "x", "nested": {"refresh_token": "x", "bank_account": "123", "safe": True}, "Authorization": "Bearer x", "pix_key": "secret"})
        self.assertEqual(log.new_values, {"name": "ok", "nested": {"safe": True}})

    def test_logs_are_append_only_at_model_and_queryset_level(self):
        log = record_audit(action=AuditAction.UPDATE, description="Imutável")
        log.description = "Alterado"
        with self.assertRaises(ValidationError):
            log.save()
        with self.assertRaises(ValidationError):
            log.delete()
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=log.pk).update(description="Alterado")
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=log.pk).delete()
        log.refresh_from_db()
        self.assertEqual(log.description, "Imutável")
