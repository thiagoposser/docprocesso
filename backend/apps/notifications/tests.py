from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notification, NotificationLevel, NotificationType
from .services import NotificationService
from apps.documents.models import DocumentCategory


class NotificationApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="notify_user", password="safe-password")
        self.other = users.objects.create_user(username="notify_other", password="safe-password")
        self.mine = NotificationService.create(user=self.user, title="Minha", message="Mensagem", type=NotificationType.SYSTEM, level=NotificationLevel.INFO, action_url="/perfil")
        self.theirs = NotificationService.create(user=self.other, title="Outra", message="Privada")

    def authenticate(self, user=None):
        self.client.force_authenticate(user or self.user)

    def test_service_and_url_validation(self):
        self.assertEqual(self.mine.user, self.user)
        self.assertEqual(self.mine.action_url, "/perfil")
        with self.assertRaises(ValidationError):
            NotificationService.create(user=self.user, title="Inválida", message="X", action_url="javascript:alert(1)")
        with self.assertRaises(ValidationError):
            NotificationService.create(user=self.user, title="Inválida", message="X", action_url="//evil.example")

    def test_user_only_sees_and_retrieves_own_notifications(self):
        self.authenticate()
        listed = self.client.get(reverse("notification-list"))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in listed.data["results"]], [self.mine.pk])
        self.assertEqual(self.client.get(reverse("notification-detail", args=[self.theirs.pk])).status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_read_read_all_and_unread_count(self):
        second = NotificationService.create(user=self.user, title="Segunda", message="Mensagem")
        self.authenticate()
        count = self.client.get(reverse("notification-unread-count"))
        self.assertEqual(count.data["count"], 2)
        marked = self.client.patch(reverse("notification-mark-read", args=[self.mine.pk]))
        self.assertTrue(marked.data["read"])
        self.assertIsNotNone(marked.data["read_at"])
        self.assertEqual(self.client.get(reverse("notification-unread-count")).data["count"], 1)
        all_read = self.client.post(reverse("notification-read-all"))
        self.assertEqual(all_read.data["updated"], 1)
        self.assertEqual(Notification.objects.filter(pk__in=[self.mine.pk, second.pk], read=False).count(), 0)

    def test_filters_pagination_and_expiration(self):
        NotificationService.create(user=self.user, title="Documento", message="Mensagem", type=NotificationType.DOCUMENT, level=NotificationLevel.WARNING)
        NotificationService.create(user=self.user, title="Expirada", message="Mensagem", expires_at=timezone.now() - timedelta(seconds=1))
        self.authenticate()
        filtered = self.client.get(reverse("notification-list"), {"read": "false", "type": "DOCUMENT", "level": "WARNING", "date_from": timezone.localdate().isoformat()})
        self.assertEqual(filtered.data["count"], 1)
        all_available = self.client.get(reverse("notification-list"))
        self.assertEqual(all_available.data["count"], 2)
        self.assertIn("results", all_available.data)

    def test_public_creation_and_foreign_mark_read_are_not_available(self):
        self.authenticate()
        self.assertEqual(self.client.post(reverse("notification-list"), {"title": "X"}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.patch(reverse("notification-mark-read", args=[self.theirs.pk])).status_code, status.HTTP_404_NOT_FOUND)

    def test_existing_generic_events_create_notifications_for_intended_recipients(self):
        admin_group = Group.objects.get(name="Administrador")
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.user.groups.add(admin_group)
        self.other.groups.add(admin_group)
        self.authenticate()

        created_user = self.client.post(reverse("user-list"), {
            "username": "notified_new_user", "password": "safe-password-2", "first_name": "Novo",
            "last_name": "Usuário", "email": "new@example.com", "group_names": ["Usuário"], "is_active": True,
        }, format="json")
        self.assertEqual(created_user.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Notification.objects.filter(user_id=created_user.data["id"], type=NotificationType.USER).exists())

        category = DocumentCategory.objects.create(name="Notificações")
        document = self.client.post(reverse("document-list"), {"title": "Novo documento", "category": category.pk, "external_url": "https://example.com", "active": True}, format="json")
        self.assertEqual(document.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Notification.objects.filter(user=self.user, type=NotificationType.DOCUMENT, action_url=f'/documentos/{document.data["id"]}').exists())

        settings = self.client.patch(reverse("core:settings-admin"), {"system_description": "Alterada"}, format="json")
        self.assertEqual(settings.status_code, status.HTTP_200_OK)
        self.assertTrue(Notification.objects.filter(user=self.other, type=NotificationType.ADMIN, action_url="/configuracoes").exists())
