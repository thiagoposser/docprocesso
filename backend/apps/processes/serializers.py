from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import AdministrativeProcess, ProcessStatus, ProcessType
from .services import create_process


class ProcessTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessType
        fields = ("id", "name", "code", "description")


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
    protected_fields = {
        "number", "created_by", "current_sector", "status", "version",
        "opened_at", "completed_at", "archived_at", "created_at", "updated_at",
    }

    class Meta:
        model = AdministrativeProcess
        fields = ("title", "description", "process_type", "origin_sector", "assignee")

    def to_internal_value(self, data):
        attempted = self.protected_fields.intersection(data)
        if attempted:
            raise serializers.ValidationError({field: "Este campo só pode ser alterado por uma ação de domínio." for field in sorted(attempted)})
        return super().to_internal_value(data)

    def validate_process_type(self, value):
        if not value.active and (not self.instance or value != self.instance.process_type):
            raise serializers.ValidationError("Selecione um tipo de processo ativo.")
        return value

    def validate_origin_sector(self, value):
        if self.instance and value != self.instance.origin_sector:
            raise serializers.ValidationError("O setor de origem não pode ser alterado por este endpoint.")
        if not value.active and (not self.instance or value != self.instance.origin_sector):
            raise serializers.ValidationError("Selecione um setor de origem ativo.")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.status != ProcessStatus.DRAFT:
            raise serializers.ValidationError("Somente processos em rascunho podem ser editados por este endpoint.")
        return attrs

    def create(self, validated_data):
        try:
            return create_process(user=self.context["request"].user, **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        try:
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return instance
