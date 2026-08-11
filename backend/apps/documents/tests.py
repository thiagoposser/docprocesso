import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Attachment, Document, DocumentCategory, safe_original_filename
from apps.audit.models import AuditAction, AuditLog
from apps.processes.models import AdministrativeProcess, ProcessEventType, ProcessStatus, ProcessType
from apps.sectors.models import Sector, UserSectorMembership


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

    def test_logical_document_allows_no_legacy_source_but_rejects_two(self):
        document = Document(title="Documento lógico", category=self.category, created_by=self.admin)
        document.full_clean()
        document.file = SimpleUploadedFile("arquivo.pdf", b"%PDF-1.4", content_type="application/pdf")
        document.external_url = "https://example.com/documento"
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_legacy_endpoint_still_requires_exactly_one_source(self):
        self.authenticate(self.admin)
        response = self.client.post(
            reverse("document-list"),
            {"title": "Sem origem", "category": self.category.pk, "active": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
        self.assertEqual(downloaded["X-Content-Type-Options"], "nosniff")
        self.assertEqual(downloaded["Cache-Control"], "private, no-store")
        self.assertEqual(downloaded["Content-Security-Policy"], "sandbox")
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.DOCUMENT_DOWNLOAD, entity_id=str(document.pk)).exists())

    def test_upload_rejects_extension_mime_and_size(self):
        self.authenticate(self.admin)
        base = {"title": "Inválido", "category": self.category.pk, "active": True}
        executable = SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream")
        self.assertEqual(self.client.post(reverse("document-list"), {**base, "file": executable}, format="multipart").status_code, status.HTTP_400_BAD_REQUEST)
        spoofed = SimpleUploadedFile("imagem.jpg", b"script", content_type="text/html")
        self.assertEqual(self.client.post(reverse("document-list"), {**base, "file": spoofed}, format="multipart").status_code, status.HTTP_400_BAD_REQUEST)
        signature_spoofed = SimpleUploadedFile("imagem.jpg", b"script", content_type="image/jpeg")
        self.assertEqual(self.client.post(reverse("document-list"), {**base, "file": signature_spoofed}, format="multipart").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(safe_original_filename("..\\..\\segredo.pdf"), "segredo.pdf")
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

    def test_document_supports_multiple_attachments_with_exactly_one_source(self):
        document = Document.objects.create(title="Dossiê", category=self.category, created_by=self.admin)
        file_attachment = Attachment.objects.create(
            document=document,
            file=SimpleUploadedFile("anexo.pdf", b"%PDF-1.4", content_type="application/pdf"),
            original_file_name="anexo.pdf",
            created_by=self.admin,
        )
        url_attachment = Attachment.objects.create(
            document=document, external_url="https://example.com/anexo", created_by=self.admin,
        )

        self.assertEqual(document.attachments.count(), 2)
        self.assertEqual((file_attachment.source_type, url_attachment.source_type), ("file", "external_url"))
        with self.assertRaises(ValidationError):
            Attachment.objects.create(document=document, created_by=self.admin)
        with self.assertRaises(ValidationError):
            Attachment.objects.create(
                document=document,
                file=SimpleUploadedFile("duplo.pdf", b"%PDF", content_type="application/pdf"),
                external_url="https://example.com/duplo",
                created_by=self.admin,
            )

    def test_attachment_is_logically_removed_and_terminal_process_blocks_inclusion(self):
        sector = Sector.objects.create(name="Documentos encerrados", code="DOC-END")
        process_type = ProcessType.objects.create(name="Documental", code="documental")
        process = AdministrativeProcess.objects.create(
            title="Encerrado", process_type=process_type, created_by=self.admin,
            origin_sector=sector, current_sector=sector, status=ProcessStatus.COMPLETED,
            completed_at="2026-08-11T12:00:00Z",
        )
        document = Document.objects.create(title="Documento do processo", category=self.category, created_by=self.admin, process=process)
        with self.assertRaisesMessage(ValidationError, "processo encerrado"):
            Attachment.objects.create(document=document, external_url="https://example.com/bloqueado", created_by=self.admin)

        independent = Document.objects.create(title="Independente", category=self.category, created_by=self.admin)
        attachment = Attachment.objects.create(document=independent, external_url="https://example.com/ativo", created_by=self.admin)
        attachment.active = False
        attachment.deactivated_at = "2026-08-11T12:00:00Z"
        attachment.save()
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk, active=False).exists())
        with self.assertRaisesMessage(ValidationError, "removidos logicamente"):
            attachment.delete()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProcessDocumentApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        media_root = str(cls._overridden_settings["MEDIA_ROOT"])
        super().tearDownClass()
        shutil.rmtree(media_root, ignore_errors=True)

    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="process_document_user")
        self.outsider = users.objects.create_user(username="process_document_outsider")
        self.sector = Sector.objects.create(name="Documentos do processo", code="DOC-PROC")
        self.other_sector = Sector.objects.create(name="Documentos restritos", code="DOC-OTHER")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        UserSectorMembership.objects.create(user=self.outsider, sector=self.other_sector, is_primary=True)
        process_type = ProcessType.objects.create(name="Processo documental", code="processo-documental")
        self.process = AdministrativeProcess.objects.create(
            title="Processo com anexos", process_type=process_type, created_by=self.user,
            origin_sector=self.sector, current_sector=self.sector,
        )
        self.category = DocumentCategory.objects.create(name="Documentos processuais")
        permissions = Permission.objects.filter(codename__in={
            "view_administrativeprocess", "view_document", "add_document", "change_document",
            "view_attachment", "add_attachment", "change_attachment",
        })
        self.user.user_permissions.add(*permissions)
        self.outsider.user_permissions.add(*permissions)
        self.client.force_authenticate(self.user)

    def test_process_document_and_multiple_attachments_hide_physical_sources(self):
        created = self.client.post(
            reverse("process-documents", args=[self.process.pk]),
            {"title": "Contrato", "description": "Versão assinada", "category": self.category.pk},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        document_id = created.data["id"]
        self.assertEqual(created.data["process"], self.process.pk)

        file_response = self.client.post(
            reverse("document-attachments", args=[document_id]),
            {"file": SimpleUploadedFile("contrato.pdf", b"%PDF-1.4", content_type="application/pdf")},
            format="multipart",
        )
        url_response = self.client.post(
            reverse("document-attachments", args=[document_id]),
            {"external_url": "https://example.com/contrato"}, format="json",
        )
        self.assertEqual(file_response.status_code, status.HTTP_201_CREATED, file_response.data)
        self.assertEqual(url_response.status_code, status.HTTP_201_CREATED, url_response.data)
        self.assertNotIn("file", file_response.data)
        self.assertNotIn("external_url", url_response.data)
        self.assertEqual(Document.objects.get(pk=document_id).attachments.count(), 2)

        listed = self.client.get(reverse("process-documents", args=[self.process.pk]))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["results"][0]["attachments"][0]["download_url"], file_response.data["download_url"])
        updated = self.client.patch(reverse("document-detail", args=[document_id]), {"title": "Contrato atualizado"})
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
        self.assertTrue(self.process.events.filter(event_type=ProcessEventType.DOCUMENT_CHANGED).count() >= 4)

    def test_download_is_authorized_and_deactivation_is_logical(self):
        document = Document.objects.create(
            title="Arquivo protegido", category=self.category, process=self.process, created_by=self.user,
        )
        attachment = Attachment.objects.create(
            document=document,
            file=SimpleUploadedFile("protegido.pdf", b"%PDF-1.4", content_type="application/pdf"),
            original_file_name="protegido.pdf", created_by=self.user,
        )
        downloaded = self.client.get(reverse("attachment-download", args=[attachment.pk]))
        self.assertEqual(downloaded.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.DOCUMENT_DOWNLOAD, entity_id=str(attachment.pk)).exists())

        deactivated = self.client.patch(reverse("attachment-deactivate", args=[attachment.pk]), {}, format="json")
        self.assertEqual(deactivated.status_code, status.HTTP_200_OK)
        attachment.refresh_from_db()
        self.assertFalse(attachment.active)
        self.assertIsNotNone(attachment.deactivated_at)
        self.assertEqual(self.client.get(reverse("attachment-download", args=[attachment.pk])).status_code, status.HTTP_404_NOT_FOUND)

        external = Attachment.objects.create(
            document=document, external_url="https://example.com/autorizado", created_by=self.user,
        )
        external_download = self.client.get(reverse("attachment-download", args=[external.pk]))
        self.assertEqual(external_download.status_code, status.HTTP_200_OK)
        self.assertEqual(external_download.data, {"external_url": "https://example.com/autorizado"})

    def test_sector_isolation_prevents_idor_for_documents_and_downloads(self):
        document = Document.objects.create(
            title="Documento restrito", category=self.category, process=self.process, created_by=self.user,
        )
        attachment = Attachment.objects.create(
            document=document, external_url="https://example.com/restrito", created_by=self.user,
        )
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(reverse("process-documents", args=[self.process.pk])).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse("document-detail", args=[document.pk])).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse("attachment-download", args=[attachment.pk])).status_code, status.HTTP_404_NOT_FOUND)

    def test_new_upload_reuses_extension_mime_and_size_validation(self):
        document = Document.objects.create(
            title="Validação", category=self.category, process=self.process, created_by=self.user,
        )
        response = self.client.post(
            reverse("document-attachments", args=[document.pk]),
            {"file": SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream")},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.process.status = ProcessStatus.COMPLETED
        self.process.completed_at = "2026-08-11T12:00:00Z"
        self.process.save()
        terminal = self.client.post(
            reverse("document-attachments", args=[document.pk]),
            {"external_url": "https://example.com/bloqueado"}, format="json",
        )
        self.assertEqual(terminal.status_code, status.HTTP_400_BAD_REQUEST)


class DocumentAttachmentMigrationTests(TransactionTestCase):
    migrate_from = [("documents", "0001_initial")]
    migrate_to = [("documents", "0002_document_process_attachment")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        User = old_apps.get_model("users", "User")
        Category = old_apps.get_model("documents", "DocumentCategory")
        LegacyDocument = old_apps.get_model("documents", "Document")
        user = User.objects.create(username="legacy_document_owner")
        category = Category.objects.create(name="Legado", slug="legado")
        self.file_document_id = LegacyDocument.objects.create(
            title="Arquivo legado", category=category, created_by=user,
            file="documents/2026/08/legacy.pdf", original_file_name="legacy.pdf",
        ).pk
        self.url_document_id = LegacyDocument.objects.create(
            title="URL legada", category=category, created_by=user,
            external_url="https://example.com/legacy",
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_copies_legacy_sources_without_removing_original_fields(self):
        MigratedDocument = self.apps.get_model("documents", "Document")
        MigratedAttachment = self.apps.get_model("documents", "Attachment")

        file_document = MigratedDocument.objects.get(pk=self.file_document_id)
        file_attachment = MigratedAttachment.objects.get(document_id=self.file_document_id)
        url_document = MigratedDocument.objects.get(pk=self.url_document_id)
        url_attachment = MigratedAttachment.objects.get(document_id=self.url_document_id)

        self.assertEqual(file_document.file.name, "documents/2026/08/legacy.pdf")
        self.assertEqual(file_attachment.file.name, file_document.file.name)
        self.assertEqual(file_attachment.original_file_name, "legacy.pdf")
        self.assertEqual(url_document.external_url, "https://example.com/legacy")
        self.assertEqual(url_attachment.external_url, url_document.external_url)
