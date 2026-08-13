from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.sectors.models import Sector

from .models import AdministrativeProcess, AdministrativeWorkflow, ProcessStatus, ProcessType
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
        fields = ("id", "code", "name", "description", "active", "version", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

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


class ProcessListSerializer(serializers.ModelSerializer):
    process_type_name = serializers.CharField(source="process_type.name", read_only=True)
    origin_sector_name = serializers.CharField(source="origin_sector.name", read_only=True)
    current_sector_name = serializers.CharField(source="current_sector.name", read_only=True, allow_null=True)
    assignee_name = serializers.CharField(source="assignee.full_name", read_only=True, allow_null=True)

    class Meta:
        model = AdministrativeProcess
        fields = (
            "id", "number", "title", "process_type", "process_type_name", "status", "version",
            "origin_sector", "origin_sector_name", "current_sector", "current_sector_name",
            "assignee", "assignee_name", "opened_at", "completed_at", "archived_at", "updated_at",
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
    note = serializers.CharField(read_only=True, allow_blank=True)
    payload = serializers.DictField(read_only=True)
    status_before = serializers.CharField(read_only=True, allow_null=True)
    status_before_label = serializers.CharField(read_only=True, allow_null=True)
    status_after = serializers.CharField(read_only=True, allow_null=True)
    status_after_label = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
