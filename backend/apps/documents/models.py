import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def document_upload_path(instance, filename):
    """Never expose a user-provided filename in storage paths."""
    extension = Path(filename).suffix.lower()
    uploaded_at = instance.created_at or timezone.now()
    return f"documents/{uploaded_at:%Y/%m}/{uuid.uuid4().hex}{extension}"


def attachment_upload_path(instance, filename):
    """Keep attachments in opaque paths without changing the existing media root."""
    extension = Path(filename).suffix.lower()
    uploaded_at = instance.created_at or timezone.now()
    return f"documents/attachments/{uploaded_at:%Y/%m}/{uuid.uuid4().hex}{extension}"


def safe_original_filename(filename):
    name = Path((filename or "arquivo").replace("\\", "/")).name
    return "".join(character for character in name if character.isprintable() and character not in {'"', "\r", "\n"})[:255] or "arquivo"


def _matches_file_signature(extension, header):
    signatures = {
        "pdf": (b"%PDF-",), "png": (b"\x89PNG\r\n\x1a\n",),
        "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",),
        "doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
        "xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
        "docx": (b"PK\x03\x04",), "xlsx": (b"PK\x03\x04",),
    }
    if extension == "txt":
        try:
            header.decode("utf-8")
            return b"\x00" not in header
        except UnicodeDecodeError:
            return False
    return any(header.startswith(signature) for signature in signatures.get(extension, ()))


def validate_document_file(upload):
    extension = Path(upload.name).suffix.lower().lstrip(".")
    if extension not in settings.DOCUMENT_ALLOWED_EXTENSIONS:
        raise ValidationError(f"Extensão .{extension or '(ausente)'} não permitida.")
    limit = settings.DOCUMENT_MAX_UPLOAD_MB * 1024 * 1024
    if upload.size > limit:
        raise ValidationError(f"O arquivo excede o limite de {settings.DOCUMENT_MAX_UPLOAD_MB} MB.")
    allowed_mime_types = {
        "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain", "image/png", "image/jpeg",
    }
    content_type = getattr(upload, "content_type", None)
    if content_type and content_type not in allowed_mime_types:
        raise ValidationError("O tipo de conteúdo do arquivo não é permitido.")
    position = upload.tell() if hasattr(upload, "tell") else 0
    header = upload.read(16)
    if hasattr(upload, "seek"):
        upload.seek(position)
    if not _matches_file_signature(extension, header):
        raise ValidationError("A assinatura do arquivo não corresponde à extensão informada.")


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoria de documento"
        verbose_name_plural = "categorias de documentos"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "categoria"
            candidate = base_slug
            suffix = 2
            while DocumentCategory.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DocumentRole(models.TextChoices):
    GENERAL = "GENERAL", "Documento geral"
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT", "Comprovante de pagamento"


class Document(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, related_name="documents")
    process = models.ForeignKey(
        "processes.AdministrativeProcess",
        on_delete=models.PROTECT,
        related_name="documents",
        blank=True,
        null=True,
    )
    role = models.CharField(max_length=24, choices=DocumentRole.choices, default=DocumentRole.GENERAL, db_index=True)
    file = models.FileField(upload_to=document_upload_path, validators=[validate_document_file], blank=True)
    original_file_name = models.CharField(max_length=255, blank=True, editable=False)
    external_url = models.URLField(max_length=1000, blank=True, validators=[URLValidator(schemes=["http", "https"])])
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        permissions = [("manage_document", "Pode gerenciar documentos")]

    def clean(self):
        super().clean()
        if self.file and self.external_url:
            raise ValidationError("Informe um arquivo ou uma URL externa, mas não ambos.")

    @property
    def source_type(self):
        return "file" if self.file else "external_url"

    def __str__(self):
        return self.title


class AttachmentQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Anexos devem ser removidos logicamente e não podem ser excluídos.")


class Attachment(models.Model):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="attachments")
    file = models.FileField(upload_to=attachment_upload_path, validators=[validate_document_file], blank=True)
    original_file_name = models.CharField(max_length=255, blank=True, editable=False)
    external_url = models.URLField(max_length=1000, blank=True, validators=[URLValidator(schemes=["http", "https"])])
    active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_attachments")
    workflow_version = models.ForeignKey(
        "processes.WorkflowVersion", on_delete=models.PROTECT,
        related_name="attachments", blank=True, null=True,
    )
    stage = models.ForeignKey(
        "processes.WorkflowStage", on_delete=models.PROTECT,
        related_name="attachments", blank=True, null=True,
    )
    sector = models.ForeignKey(
        "sectors.Sector", on_delete=models.PROTECT,
        related_name="document_attachments", blank=True, null=True,
    )
    function = models.ForeignKey(
        "sectors.OrganizationalFunction", on_delete=models.PROTECT,
        related_name="document_attachments", blank=True, null=True,
    )
    context_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(blank=True, null=True)

    objects = AttachmentQuerySet.as_manager()

    class Meta:
        ordering = ["created_at", "id"]
        default_permissions = ("add", "change", "view")
        permissions = [("manage_attachment", "Pode gerenciar anexos")]
        indexes = [models.Index(fields=["document", "active", "created_at"], name="attachment_doc_active_idx")]
        verbose_name = "anexo"
        verbose_name_plural = "anexos"

    def clean(self):
        super().clean()
        if self.pk:
            historical_fields = (
                "workflow_version_id", "stage_id", "sector_id", "function_id", "context_snapshot"
            )
            previous = Attachment.objects.filter(pk=self.pk).values(*historical_fields).first()
            if previous and any(previous[field] != getattr(self, field) for field in historical_fields):
                raise ValidationError("O contexto histórico do anexo é imutável.")
        if bool(self.file) == bool(self.external_url):
            raise ValidationError("Informe um arquivo ou uma URL externa, mas não ambos.")
        activating = self.active
        if self.pk:
            previous_active = Attachment.objects.filter(pk=self.pk).values_list("active", flat=True).first()
            activating = previous_active is False and self.active
        if activating and self.document_id and self.document.process_id:
            from apps.processes.models import ProcessStatus

            blocked = {ProcessStatus.CANCELLED, ProcessStatus.ARCHIVED}
            if self.document.role != DocumentRole.PAYMENT_RECEIPT:
                blocked.add(ProcessStatus.COMPLETED)
            if self.document.process.status in blocked:
                raise ValidationError({"document": "Não é possível incluir anexos em um processo encerrado."})

    @property
    def source_type(self):
        return "file" if self.file else "external_url"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Anexos devem ser removidos logicamente e não podem ser excluídos.")

    def __str__(self):
        return self.original_file_name or self.external_url or f"Anexo {self.pk or ''}".strip()
