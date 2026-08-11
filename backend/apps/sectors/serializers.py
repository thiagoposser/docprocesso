from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Sector


class SectorSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)

    class Meta:
        model = Sector
        fields = (
            "id", "name", "code", "parent", "parent_name", "manager", "manager_name",
            "active", "created_at", "updated_at",
        )
        read_only_fields = ("id", "parent_name", "manager_name", "created_at", "updated_at")

    def validate(self, attrs):
        parent = attrs.get("parent") if "parent" in attrs else None
        if "parent" in attrs and parent and not parent.active:
            raise serializers.ValidationError({"parent": "Selecione um setor pai ativo."})

        active = attrs.get("active", getattr(self.instance, "active", True))
        if self.instance and not active and self.instance.children.filter(active=True).exists():
            raise serializers.ValidationError({"active": "Inative primeiro os setores filhos ativos."})
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
