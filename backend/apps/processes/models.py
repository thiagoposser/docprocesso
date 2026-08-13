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


class ProcessMovementAction(models.TextChoices):
    OPEN = "OPEN", "Abertura"
    FORWARD = "FORWARD", "Encaminhamento"
    RECEIVE = "RECEIVE", "Recebimento"
    RETURN = "RETURN", "Devolução"
    COMPLETE = "COMPLETE", "Conclusão"
    REOPEN = "REOPEN", "Reabertura"
    CANCEL = "CANCEL", "Cancelamento"
    ARCHIVE = "ARCHIVE", "Arquivamento"


class ProcessEventType(models.TextChoices):
    PROCESS_CREATED = "PROCESS_CREATED", "Processo criado"
    DOCUMENT_CHANGED = "DOCUMENT_CHANGED", "Documento alterado"
    DUE_DATE_CHANGED = "DUE_DATE_CHANGED", "Vencimento alterado"
    PAYMENT_CHANGED = "PAYMENT_CHANGED", "Pagamento alterado"
    CORRECTION = "CORRECTION", "Correção de histórico"
    NOTE = "NOTE", "Observação funcional"
    SYSTEM = "SYSTEM", "Evento de sistema"


class ProcessType(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True, db_index=True)
    workflow = models.ForeignKey(
        "AdministrativeWorkflow", on_delete=models.PROTECT, related_name="process_types", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        default_permissions = ("add", "change", "view")
        verbose_name = "tipo de processo"
        verbose_name_plural = "tipos de processo"

    def __str__(self):
        return f"{self.code} - {self.name}"


class AdministrativeWorkflow(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    active = models.BooleanField(default=True, db_index=True)
    current_version = models.ForeignKey(
        "WorkflowVersion", on_delete=models.PROTECT, related_name="current_for_workflows", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code", "id"]
        verbose_name = "fluxo administrativo"
        verbose_name_plural = "fluxos administrativos"

    def __str__(self):
        return self.current_version.name if self.current_version_id else self.code


class WorkflowVersion(models.Model):
    workflow = models.ForeignKey(AdministrativeWorkflow, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["workflow_id", "-version"]
        constraints = [models.UniqueConstraint(fields=["workflow", "version"], name="unique_workflow_version")]

    def __str__(self):
        return f"{self.name} v{self.version}"


class WorkflowStage(models.Model):
    workflow_version = models.ForeignKey(WorkflowVersion, on_delete=models.PROTECT, related_name="stages")
    order = models.PositiveIntegerField()
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_initial = models.BooleanField(default=False)
    is_final = models.BooleanField(default=False)
    responsible_sector = models.ForeignKey(
        "sectors.Sector", on_delete=models.PROTECT, related_name="workflow_stages", null=True, blank=True
    )
    responsible_function = models.ForeignKey(
        "sectors.OrganizationalFunction", on_delete=models.PROTECT, related_name="workflow_stages", null=True, blank=True
    )
    requires_manager = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["workflow_version_id", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["workflow_version", "order"], name="unique_workflow_stage_order"),
            models.UniqueConstraint(fields=["workflow_version"], condition=models.Q(is_initial=True), name="unique_initial_stage_per_version"),
            models.UniqueConstraint(fields=["workflow_version"], condition=models.Q(is_final=True), name="unique_final_stage_per_version"),
            models.CheckConstraint(condition=models.Q(order__gte=1), name="workflow_stage_order_gte_1"),
            models.CheckConstraint(
                condition=models.Q(responsible_sector__isnull=False) | models.Q(responsible_function__isnull=False),
                name="workflow_stage_has_responsibility",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.responsible_sector_id and not self.responsible_sector.active:
            errors["responsible_sector"] = "Selecione um setor ativo para uma nova configuração."
        if self.responsible_function_id and not self.responsible_function.active:
            errors["responsible_function"] = "Selecione uma função ativa para uma nova configuração."
        if self.workflow_version_id and self.workflow_version.workflow.current_version_id != self.workflow_version_id:
            errors["workflow_version"] = "Somente a versão atual do fluxo pode receber alterações."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order}. {self.name}"


class WorkflowTransition(models.Model):
    source_stage = models.ForeignKey(WorkflowStage, on_delete=models.PROTECT, related_name="outgoing_transitions")
    destination_stage = models.ForeignKey(WorkflowStage, on_delete=models.PROTECT, related_name="incoming_transitions")
    code = models.SlugField(max_length=50)
    name = models.CharField(max_length=150)
    authorized_sector = models.ForeignKey(
        "sectors.Sector", on_delete=models.PROTECT, related_name="authorized_workflow_transitions", null=True, blank=True
    )
    authorized_function = models.ForeignKey(
        "sectors.OrganizationalFunction", on_delete=models.PROTECT,
        related_name="authorized_workflow_transitions", null=True, blank=True,
    )
    requires_note = models.BooleanField(default=False)
    requires_attachment = models.BooleanField(default=False)
    is_return = models.BooleanField(default=False)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_stage_id", "code", "id"]
        constraints = [
            models.UniqueConstraint(fields=["source_stage", "code"], name="unique_transition_code_per_source"),
            models.CheckConstraint(condition=~models.Q(source_stage=models.F("destination_stage")), name="transition_changes_stage"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.source_stage_id and self.destination_stage_id:
            if self.source_stage.workflow_version_id != self.destination_stage.workflow_version_id:
                errors["destination_stage"] = "Origem e destino devem pertencer à mesma versão do fluxo."
            if self.source_stage.workflow_version.workflow.current_version_id != self.source_stage.workflow_version_id:
                errors["source_stage"] = "Somente a versão atual pode receber alterações."
            if self.source_stage.is_final and not self.is_return:
                errors["source_stage"] = "Etapa final só pode possuir uma transição explícita de devolução."
        if self.authorized_sector_id and not self.authorized_sector.active:
            errors["authorized_sector"] = "Selecione um setor autorizado ativo."
        if self.authorized_function_id and not self.authorized_function.active:
            errors["authorized_function"] = "Selecione uma função autorizada ativa."
        if self.pk:
            previous = WorkflowTransition.objects.filter(pk=self.pk).values("code", "source_stage_id").first()
            if previous and (previous["code"] != self.code or previous["source_stage_id"] != self.source_stage_id):
                errors["code"] = "O código e a etapa de origem da transição são estáveis."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source_stage} — {self.name} → {self.destination_stage}"


class AdministrativeProcess(models.Model):
    number = models.CharField(max_length=35, unique=True, default=generate_process_number, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    process_type = models.ForeignKey(ProcessType, on_delete=models.PROTECT, related_name="processes")
    workflow_version = models.ForeignKey(
        WorkflowVersion, on_delete=models.PROTECT, related_name="processes", blank=True, null=True
    )
    current_stage = models.ForeignKey(
        WorkflowStage, on_delete=models.PROTECT, related_name="processes", blank=True, null=True
    )
    responsible_sector = models.ForeignKey(
        "sectors.Sector", on_delete=models.PROTECT, related_name="responsible_processes", blank=True, null=True
    )
    responsible_function = models.ForeignKey(
        "sectors.OrganizationalFunction", on_delete=models.PROTECT,
        related_name="responsible_processes", blank=True, null=True,
    )
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
        if self.current_stage_id and self.workflow_version_id and self.current_stage.workflow_version_id != self.workflow_version_id:
            errors["current_stage"] = "A etapa atual deve pertencer à versão de fluxo do processo."
        if bool(self.current_stage_id) != bool(self.workflow_version_id):
            errors["workflow_version"] = "Versão e etapa de fluxo devem ser informadas em conjunto."
        if self.current_stage_id and not self.responsible_sector_id:
            self.responsible_sector = self.current_stage.responsible_sector or self.origin_sector
        if self.current_stage_id and not self.responsible_sector_id:
            errors["responsible_sector"] = "Processo com fluxo deve possuir setor responsável."
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


class ProcessMovementQuerySet(models.QuerySet):
    def chronological(self):
        return self.order_by("created_at", "id")

    def for_process(self, process):
        return self.filter(process=process).chronological()

    def update(self, **kwargs):
        raise ValidationError("Movimentações são imutáveis e não podem ser atualizadas.")

    def delete(self):
        raise ValidationError("Movimentações são imutáveis e não podem ser excluídas.")


class ProcessMovement(models.Model):
    process = models.ForeignKey(AdministrativeProcess, on_delete=models.PROTECT, related_name="movements")
    workflow_version = models.ForeignKey(
        WorkflowVersion, on_delete=models.PROTECT, related_name="process_movements", blank=True, null=True
    )
    transition = models.ForeignKey(
        WorkflowTransition, on_delete=models.PROTECT, related_name="process_movements", blank=True, null=True
    )
    from_stage = models.ForeignKey(
        WorkflowStage, on_delete=models.PROTECT, related_name="outgoing_process_movements", blank=True, null=True
    )
    to_stage = models.ForeignKey(
        WorkflowStage, on_delete=models.PROTECT, related_name="incoming_process_movements", blank=True, null=True
    )
    action = models.CharField(max_length=20, choices=ProcessMovementAction.choices)
    from_sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="outgoing_process_movements",
        blank=True,
        null=True,
    )
    to_sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="incoming_process_movements",
        blank=True,
        null=True,
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="process_movements")
    from_responsible_sector = models.ForeignKey(
        Sector, on_delete=models.PROTECT, related_name="outgoing_responsibility_movements", blank=True, null=True
    )
    to_responsible_sector = models.ForeignKey(
        Sector, on_delete=models.PROTECT, related_name="incoming_responsibility_movements", blank=True, null=True
    )
    from_responsible_function = models.ForeignKey(
        "sectors.OrganizationalFunction", on_delete=models.PROTECT,
        related_name="outgoing_responsibility_movements", blank=True, null=True,
    )
    to_responsible_function = models.ForeignKey(
        "sectors.OrganizationalFunction", on_delete=models.PROTECT,
        related_name="incoming_responsibility_movements", blank=True, null=True,
    )
    from_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="outgoing_assignment_movements", blank=True, null=True,
    )
    to_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="incoming_assignment_movements", blank=True, null=True,
    )
    note = models.TextField(blank=True)
    status_before = models.CharField(max_length=20, choices=ProcessStatus.choices)
    status_after = models.CharField(max_length=20, choices=ProcessStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ProcessMovementQuerySet.as_manager()

    class Meta:
        ordering = ["created_at", "id"]
        default_permissions = ("view",)
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(action__in=[ProcessMovementAction.RETURN, ProcessMovementAction.CANCEL, ProcessMovementAction.REOPEN], note=""),
                name="movement_required_note",
            ),
            models.CheckConstraint(
                condition=~models.Q(action=ProcessMovementAction.OPEN) | models.Q(from_sector__isnull=True, to_sector__isnull=False),
                name="movement_open_sector_coherence",
            ),
            models.CheckConstraint(
                condition=~models.Q(action__in=[ProcessMovementAction.FORWARD, ProcessMovementAction.RETURN])
                | (models.Q(from_sector__isnull=False, to_sector__isnull=False) & ~models.Q(from_sector=models.F("to_sector"))),
                name="movement_transfer_sectors",
            ),
            models.CheckConstraint(
                condition=~models.Q(action=ProcessMovementAction.RECEIVE)
                | models.Q(from_sector__isnull=False, from_sector=models.F("to_sector")),
                name="movement_receive_sector",
            ),
            models.CheckConstraint(
                condition=~models.Q(action__in=[
                    ProcessMovementAction.COMPLETE,
                    ProcessMovementAction.CANCEL,
                    ProcessMovementAction.REOPEN,
                    ProcessMovementAction.ARCHIVE,
                ]) | models.Q(from_sector__isnull=False, from_sector=models.F("to_sector")),
                name="movement_state_action_sector",
            ),
        ]
        indexes = [
            models.Index(fields=["process", "created_at"], name="movement_process_date_idx"),
            models.Index(fields=["from_sector", "created_at"], name="movement_from_date_idx"),
            models.Index(fields=["to_sector", "created_at"], name="movement_to_date_idx"),
            models.Index(fields=["action", "created_at"], name="movement_action_date_idx"),
        ]
        verbose_name = "movimentação de processo"
        verbose_name_plural = "movimentações de processos"

    def clean(self):
        super().clean()
        errors = {}
        if self.action in {ProcessMovementAction.RETURN, ProcessMovementAction.CANCEL, ProcessMovementAction.REOPEN} and not self.note.strip():
            errors["note"] = "A observação é obrigatória para esta ação."
        if self.action == ProcessMovementAction.OPEN and (self.from_sector_id is not None or self.to_sector_id is None):
            errors["to_sector"] = "A abertura deve informar somente o setor de destino."
        if self.action in {ProcessMovementAction.FORWARD, ProcessMovementAction.RETURN} and (
            self.from_sector_id is None or self.to_sector_id is None or self.from_sector_id == self.to_sector_id
        ):
            errors["to_sector"] = "A ação deve informar setores de origem e destino diferentes."
        if self.action == ProcessMovementAction.RECEIVE and (
            self.from_sector_id is None or self.to_sector_id != self.from_sector_id
        ):
            errors["to_sector"] = "O recebimento deve permanecer no mesmo setor."
        if self.action in {
            ProcessMovementAction.COMPLETE,
            ProcessMovementAction.CANCEL,
            ProcessMovementAction.REOPEN,
            ProcessMovementAction.ARCHIVE,
        } and (self.from_sector_id is None or self.to_sector_id != self.from_sector_id):
            errors["to_sector"] = "A ação de estado deve permanecer no mesmo setor."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Movimentações são imutáveis e não podem ser atualizadas.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Movimentações são imutáveis e não podem ser excluídas.")

    def __str__(self):
        return f"{self.process.number} - {self.get_action_display()}"


class ProcessEventQuerySet(models.QuerySet):
    def chronological(self):
        return self.order_by("created_at", "id")

    def for_process(self, process):
        return self.filter(process=process).chronological()

    def update(self, **kwargs):
        raise ValidationError("Eventos de processo são imutáveis e não podem ser atualizados.")

    def delete(self):
        raise ValidationError("Eventos de processo são imutáveis e não podem ser excluídos.")


class ProcessEvent(models.Model):
    process = models.ForeignKey(AdministrativeProcess, on_delete=models.PROTECT, related_name="events")
    event_type = models.CharField(max_length=32, choices=ProcessEventType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="process_events",
        blank=True,
        null=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ProcessEventQuerySet.as_manager()

    class Meta:
        ordering = ["created_at", "id"]
        default_permissions = ("view",)
        indexes = [
            models.Index(fields=["process", "created_at"], name="event_process_date_idx"),
            models.Index(fields=["event_type", "created_at"], name="event_type_date_idx"),
        ]
        verbose_name = "evento funcional de processo"
        verbose_name_plural = "eventos funcionais de processos"

    def clean(self):
        super().clean()
        if not isinstance(self.payload, dict):
            raise ValidationError({"payload": "O payload do evento deve ser um objeto JSON."})

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Eventos de processo são imutáveis e não podem ser atualizados.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Eventos de processo são imutáveis e não podem ser excluídos.")

    def __str__(self):
        return f"{self.process.number} - {self.title}"
