from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.sectors.models import Sector

from .models import AdministrativeProcess, AdministrativeWorkflow, ProcessStatus, ProcessType, WorkflowStage, WorkflowTransition
from .workflow_services import create_workflow, update_workflow
from .services import create_process


class ProcessTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessType
        fields = ("id", "name", "code", "description")


class AdministrativeWorkflowSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="current_version.name", max_length=150)
    description = serializers.CharField(source="current_version.description", required=False, allow_blank=True)
    version = serializers.IntegerField(source="current_version.version", read_only=True)

    class Meta:
        model = AdministrativeWorkflow
        fields = ("id", "code", "name", "description", "active", "current_version", "version", "created_at", "updated_at")
        read_only_fields = ("current_version", "created_at", "updated_at")

    def create(self, validated_data):
        version = validated_data.pop("current_version")
        return create_workflow(**validated_data, **version)

    def validate_code(self, value):
        if self.instance and value != self.instance.code:
            raise serializers.ValidationError("O código do fluxo não pode ser alterado.")
        return value

    def update(self, instance, validated_data):
        version = validated_data.pop("current_version", {})
        return update_workflow(workflow=instance, active=validated_data.get("active"), **version)


class WorkflowStageSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="responsible_sector.name", read_only=True, allow_null=True)
    function_name = serializers.CharField(source="responsible_function.name", read_only=True, allow_null=True)

    class Meta:
        model = WorkflowStage
        fields = (
            "id", "workflow_version", "order", "name", "description", "is_initial", "is_final",
            "responsible_sector", "sector_name", "responsible_function", "function_name",
            "requires_manager", "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        version = attrs.get("workflow_version", getattr(self.instance, "workflow_version", None))
        sector = attrs.get("responsible_sector", getattr(self.instance, "responsible_sector", None))
        function = attrs.get("responsible_function", getattr(self.instance, "responsible_function", None))
        errors = {}
        if version and version.workflow.current_version_id != version.id:
            errors["workflow_version"] = "Somente a versão atual pode receber alterações."
        if not sector and not function:
            errors["responsibility"] = "Informe um setor ou uma função responsável."
        if sector and not sector.active:
            errors["responsible_sector"] = "Selecione um setor ativo."
        if function and not function.active:
            errors["responsible_function"] = "Selecione uma função ativa."
        if self.instance and "workflow_version" in attrs and version != self.instance.workflow_version:
            errors["workflow_version"] = "A etapa não pode ser movida entre versões."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source_stage.name", read_only=True)
    destination_name = serializers.CharField(source="destination_stage.name", read_only=True)
    sector_name = serializers.CharField(source="authorized_sector.name", read_only=True, allow_null=True)
    function_name = serializers.CharField(source="authorized_function.name", read_only=True, allow_null=True)

    class Meta:
        model = WorkflowTransition
        fields = (
            "id", "source_stage", "source_name", "code", "name", "destination_stage", "destination_name",
            "authorized_sector", "sector_name", "authorized_function", "function_name",
            "requires_note", "requires_attachment", "is_return", "active", "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        source = attrs.get("source_stage", getattr(self.instance, "source_stage", None))
        destination = attrs.get("destination_stage", getattr(self.instance, "destination_stage", None))
        sector = attrs.get("authorized_sector", getattr(self.instance, "authorized_sector", None))
        function = attrs.get("authorized_function", getattr(self.instance, "authorized_function", None))
        is_return = attrs.get("is_return", getattr(self.instance, "is_return", False))
        errors = {}
        if source and destination and source.workflow_version_id != destination.workflow_version_id:
            errors["destination_stage"] = "Origem e destino devem pertencer à mesma versão."
        if source and source.workflow_version.workflow.current_version_id != source.workflow_version_id:
            errors["source_stage"] = "Somente a versão atual pode receber alterações."
        if source and source.is_final and not is_return:
            errors["source_stage"] = "Etapa final só admite devolução explícita."
        if sector and not sector.active:
            errors["authorized_sector"] = "Selecione um setor ativo."
        if function and not function.active:
            errors["authorized_function"] = "Selecione uma função ativa."
        if self.instance and (attrs.get("source_stage", self.instance.source_stage) != self.instance.source_stage or attrs.get("code", self.instance.code) != self.instance.code):
            errors["code"] = "Código e origem são estáveis."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error


class ProcessListSerializer(serializers.ModelSerializer):
    process_type_name = serializers.CharField(source="process_type.name", read_only=True)
    origin_sector_name = serializers.CharField(source="origin_sector.name", read_only=True)
    current_sector_name = serializers.CharField(source="current_sector.name", read_only=True, allow_null=True)
    assignee_name = serializers.CharField(source="assignee.full_name", read_only=True, allow_null=True)
    workflow_name = serializers.CharField(source="workflow_version.name", read_only=True, allow_null=True)
    workflow_version_number = serializers.IntegerField(source="workflow_version.version", read_only=True, allow_null=True)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True, allow_null=True)
    responsible_sector_name = serializers.CharField(source="responsible_sector.name", read_only=True, allow_null=True)
    responsible_function_name = serializers.CharField(source="responsible_function.name", read_only=True, allow_null=True)

    class Meta:
        model = AdministrativeProcess
        fields = (
            "id", "number", "title", "process_type", "process_type_name", "status", "version",
            "origin_sector", "origin_sector_name", "current_sector", "current_sector_name",
            "assignee", "assignee_name", "opened_at", "completed_at", "archived_at", "updated_at",
            "workflow_version", "workflow_name", "workflow_version_number", "current_stage", "current_stage_name",
            "responsible_sector", "responsible_sector_name", "responsible_function", "responsible_function_name",
        )


class ProcessDetailSerializer(ProcessListSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta(ProcessListSerializer.Meta):
        fields = ProcessListSerializer.Meta.fields + ("description", "created_by", "created_by_name", "created_at")


class ProcessWriteSerializer(serializers.ModelSerializer):
    origin_membership = serializers.IntegerField(write_only=True, required=False)
    protected_fields = {
        "number", "created_by", "current_sector", "status", "version", "assignee",
        "origin_sector", "opened_at", "completed_at", "archived_at", "created_at", "updated_at",
    }

    class Meta:
        model = AdministrativeProcess
        fields = ("title", "description", "process_type", "origin_membership")

    def to_internal_value(self, data):
        attempted = self.protected_fields.intersection(data)
        if attempted:
            raise serializers.ValidationError({field: "Este campo só pode ser alterado por uma ação de domínio." for field in sorted(attempted)})
        return super().to_internal_value(data)

    def validate_process_type(self, value):
        if not value.active and (not self.instance or value != self.instance.process_type):
            raise serializers.ValidationError("Selecione um tipo de processo ativo.")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.status != ProcessStatus.DRAFT:
            raise serializers.ValidationError("Somente processos em rascunho podem ser editados por este endpoint.")
        if self.instance and "origin_membership" in attrs:
            raise serializers.ValidationError({"origin_membership": "A origem não pode ser alterada após a criação."})
        return attrs

    def create(self, validated_data):
        try:
            return create_process(user=self.context["request"].user, **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        validated_data.pop("origin_membership", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        try:
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return instance


class ProcessActionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, max_length=2000, default="")


class ExecuteWorkflowTransitionSerializer(ProcessActionSerializer):
    action = serializers.SlugField(max_length=50)


class EligibleAssigneeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    name = serializers.CharField(source="full_name", read_only=True)


class AssignProcessSerializer(ProcessActionSerializer):
    assignee = serializers.IntegerField(min_value=1)


class AvailableWorkflowActionSerializer(serializers.Serializer):
    action = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    destination_stage = serializers.IntegerField(read_only=True)
    destination_stage_name = serializers.CharField(read_only=True)
    requires_note = serializers.BooleanField(read_only=True)
    requires_attachment = serializers.BooleanField(read_only=True)
    is_return = serializers.BooleanField(read_only=True)


class ProcessDestinationActionSerializer(ProcessActionSerializer):
    destination = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.filter(active=True))


class ProcessRequiredNoteActionSerializer(ProcessActionSerializer):
    note = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True, max_length=2000)


class ProcessReturnActionSerializer(ProcessDestinationActionSerializer):
    note = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True, max_length=2000)


class ProcessTimelineEntrySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("movement", "event"), read_only=True)
    id = serializers.CharField(read_only=True)
    action = serializers.CharField(read_only=True, allow_null=True)
    action_label = serializers.CharField(read_only=True, allow_null=True)
    event_type = serializers.CharField(read_only=True, allow_null=True)
    event_type_label = serializers.CharField(read_only=True, allow_null=True)
    title = serializers.CharField(read_only=True)
    actor = serializers.IntegerField(read_only=True, allow_null=True)
    actor_name = serializers.CharField(read_only=True, allow_null=True)
    from_sector = serializers.IntegerField(read_only=True, allow_null=True)
    from_sector_name = serializers.CharField(read_only=True, allow_null=True)
    to_sector = serializers.IntegerField(read_only=True, allow_null=True)
    to_sector_name = serializers.CharField(read_only=True, allow_null=True)
    workflow_version = serializers.IntegerField(read_only=True, allow_null=True)
    workflow_version_number = serializers.IntegerField(read_only=True, allow_null=True)
    transition = serializers.IntegerField(read_only=True, allow_null=True)
    transition_code = serializers.CharField(read_only=True, allow_null=True)
    from_stage = serializers.IntegerField(read_only=True, allow_null=True)
    from_stage_name = serializers.CharField(read_only=True, allow_null=True)
    to_stage = serializers.IntegerField(read_only=True, allow_null=True)
    to_stage_name = serializers.CharField(read_only=True, allow_null=True)
    from_responsibility = serializers.CharField(read_only=True, allow_null=True)
    to_responsibility = serializers.CharField(read_only=True, allow_null=True)
    context_snapshot = serializers.DictField(read_only=True)
    note = serializers.CharField(read_only=True, allow_blank=True)
    payload = serializers.DictField(read_only=True)
    status_before = serializers.CharField(read_only=True, allow_null=True)
    status_before_label = serializers.CharField(read_only=True, allow_null=True)
    status_after = serializers.CharField(read_only=True, allow_null=True)
    status_after_label = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
