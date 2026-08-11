import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.sectors.models import Sector


def generate_process_number():
    """Generate an opaque, concurrency-safe number without imposing an annual sequence."""
    return f"DP-{uuid.uuid4().hex.upper()}"


class ProcessStatus(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    OPEN = "OPEN", "Aberto"
    IN_PROGRESS = "IN_PROGRESS", "Em andamento"
    COMPLETED = "COMPLETED", "Concluído"
    CANCELLED = "CANCELLED", "Cancelado"
    ARCHIVED = "ARCHIVED", "Arquivado"


class ProcessType(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        default_permissions = ("add", "change", "view")
        verbose_name = "tipo de processo"
        verbose_name_plural = "tipos de processo"

    def __str__(self):
        return f"{self.code} - {self.name}"


class AdministrativeProcess(models.Model):
    number = models.CharField(max_length=35, unique=True, default=generate_process_number, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    process_type = models.ForeignKey(ProcessType, on_delete=models.PROTECT, related_name="processes")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_processes",
    )
    origin_sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="originated_processes")
    current_sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="current_processes",
        blank=True,
        null=True,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_processes",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=ProcessStatus.choices, default=ProcessStatus.DRAFT, db_index=True)
    version = models.PositiveIntegerField(default=1)
    opened_at = models.DateTimeField(blank=True, null=True, db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True, db_index=True)
    archived_at = models.DateTimeField(blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        default_permissions = ("add", "change", "view")
        permissions = [
            ("open_administrativeprocess", "Pode abrir processos"),
            ("forward_administrativeprocess", "Pode encaminhar processos"),
            ("receive_administrativeprocess", "Pode receber processos"),
            ("return_administrativeprocess", "Pode devolver processos"),
            ("complete_administrativeprocess", "Pode concluir processos"),
            ("reopen_administrativeprocess", "Pode reabrir processos"),
            ("cancel_administrativeprocess", "Pode cancelar processos"),
            ("archive_administrativeprocess", "Pode arquivar processos"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(version__gte=1), name="process_version_gte_1"),
            models.CheckConstraint(
                condition=models.Q(status=ProcessStatus.DRAFT) | models.Q(current_sector__isnull=False),
                name="process_current_sector_outside_draft",
            ),
        ]
        indexes = [
            models.Index(fields=["current_sector", "status"], name="process_sector_status_idx"),
            models.Index(fields=["process_type", "status"], name="process_type_status_idx"),
        ]
        verbose_name = "processo administrativo"
        verbose_name_plural = "processos administrativos"

    def clean(self):
        super().clean()
        errors = {}
        if self.status != ProcessStatus.DRAFT and self.current_sector_id is None:
            errors["current_sector"] = "O setor atual é obrigatório fora do rascunho."
        if self.status == ProcessStatus.COMPLETED and self.completed_at is None:
            errors["completed_at"] = "A data de conclusão é obrigatória para processos concluídos."
        if self.status == ProcessStatus.ARCHIVED and self.archived_at is None:
            errors["archived_at"] = "A data de arquivamento é obrigatória para processos arquivados."
        if self.version < 1:
            errors["version"] = "A versão deve ser maior ou igual a 1."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} - {self.title}"
