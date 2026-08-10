import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Document, DocumentCategory
from apps.audit.models import AuditAction, AuditLog


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        media_root = str(cls._overridden_settings["MEDIA_ROOT"])
        super().tearDownClass()
        shutil.rmtree(media_root, ignore_errors=True)

    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(username="doc_admin", password="safe-password", is_staff=True)
        self.user = user_model.objects.create_user(username="doc_user", password="safe-password")
        self.user.groups.add(Group.objects.get(name="Usuário"))
        self.category = DocumentCategory.objects.create(name="Geral")

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def test_model_requires_exactly_one_source(self):
        document = Document(title="Inválido", category=self.category, created_by=self.admin)
        with self.assertRaises(ValidationError):
            document.full_clean()
        document.file = SimpleUploadedFile("arquivo.pdf", b"%PDF-1.4", content_type="application/pdf")
        document.external_url = "https://example.com/documento"
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_admin_creates_upload_with_safe_name_and_dashboard_counts_it(self):
        self.authenticate(self.admin)
        response = self.client.post(reverse("document-list"), {
            "title": "Manual", "description": "Manual do sistema", "category": self.category.pk,
            "file": SimpleUploadedFile("nome perigoso.PDF", b"%PDF-1.4 test", content_type="application/pdf"), "active": True,
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        document = Document.objects.get()
        self.assertEqual(document.created_by, self.admin)
        self.assertNotIn("nome perigoso", document.file.name)
        self.assertEqual(self.client.get(reverse("core:dashboard")).data["total_documents"], 1)
        downloaded = self.client.get(reverse("document-download", args=[document.pk]))
        self.assertEqual(downloaded.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.DOCUMENT_DOWNLOAD, entity_id=str(document.pk)).exists())

    def test_upload_rejects_extension_mime_and_size(self):
        self.authenticate(self.admin)
        base = {"title": "Inválido", "category": self.category.pk, "active": True}
        executable = SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream")
        self.assertEqual(self.client.post(reverse("document-list"), {**base, "file": executable}, format="multipart").status_code, status.HTTP_400_BAD_REQUEST)
        spoofed = SimpleUploadedFile("imagem.jpg", b"script", content_type="text/html")
        self.assertEqual(self.client.post(reverse("document-list"), {**base, "file": spoofed}, format="multipart").status_code, status.HTTP_400_BAD_REQUEST)
        with override_settings(DOCUMENT_MAX_UPLOAD_MB=0):
            oversized = SimpleUploadedFile("arquivo.txt", b"x", content_type="text/plain")
            self.assertEqual(self.client.post(reverse("document-list"), {**base, "file": oversized}, format="multipart").status_code, status.HTTP_400_BAD_REQUEST)

    def test_regular_user_sees_only_active_documents_and_cannot_write(self):
        active = Document.objects.create(title="Ativo", category=self.category, external_url="https://example.com/a", created_by=self.admin)
        inactive = Document.objects.create(title="Inativo", category=self.category, external_url="https://example.com/i", created_by=self.admin, active=False)
        self.authenticate(self.user)
        listed = self.client.get(reverse("document-list"))
        self.assertEqual([item["id"] for item in listed.data["results"]], [active.pk])
        self.assertEqual(self.client.get(reverse("document-detail", args=[inactive.pk])).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(reverse("document-list"), {"title": "X"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(reverse("document-detail", args=[active.pk]), {"active": False}).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_filters_searches_orders_updates_and_manages_categories(self):
        second = DocumentCategory.objects.create(name="Políticas")
        document = Document.objects.create(title="Política interna", description="Segurança", category=second, external_url="https://example.com", created_by=self.admin)
        self.authenticate(self.admin)
        listed = self.client.get(reverse("document-list"), {"search": "segurança", "category": second.pk, "active": "true", "ordering": "title"})
        self.assertEqual(listed.data["count"], 1)
        updated = self.client.patch(reverse("document-detail", args=[document.pk]), {"active": False}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        created_category = self.client.post(reverse("document-category-list"), {"name": "Contratos", "active": True})
        self.assertEqual(created_category.status_code, status.HTTP_201_CREATED)
