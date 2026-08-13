from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .membership_services import save_membership
from .models import OrganizationalFunction, OrganizationalUnit, Sector, UserSectorMembership


class OrganizationalFunctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationalFunction
        fields = ("id", "name", "code", "description", "active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

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


class OrganizationalUnitSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = OrganizationalUnit
        fields = (
            "id", "name", "acronym", "description", "parent", "parent_name",
            "active", "created_at", "updated_at",
        )
        read_only_fields = ("id", "parent_name", "created_at", "updated_at")

    def validate(self, attrs):
        parent = attrs.get("parent") if "parent" in attrs else None
        parent_changed = "parent" in attrs and (not self.instance or parent != self.instance.parent)
        if parent_changed and parent and not parent.active:
            raise serializers.ValidationError({"parent": "Selecione uma unidade superior ativa."})

        active = attrs.get("active", getattr(self.instance, "active", True))
        if self.instance and not active and self.instance.children.filter(active=True).exists():
            raise serializers.ValidationError({"active": "Inative primeiro as unidades subordinadas ativas."})
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


class SectorSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    unit_acronym = serializers.CharField(source="unit.acronym", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)

    class Meta:
        model = Sector
        fields = (
            "id", "unit", "unit_name", "unit_acronym", "name", "code",
            "parent", "parent_name", "manager", "manager_name",
            "active", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "unit_name", "unit_acronym", "parent_name", "manager_name",
            "created_at", "updated_at",
        )

    def validate(self, attrs):
        unit = attrs.get("unit", getattr(self.instance, "unit", None))
        unit_changed = "unit" in attrs and (not self.instance or unit != self.instance.unit)
        if not self.instance and unit is None:
            raise serializers.ValidationError({"unit": "Selecione a unidade do setor."})
        if unit_changed and unit and not unit.active:
            raise serializers.ValidationError({"unit": "Selecione uma unidade ativa."})

        parent = attrs.get("parent") if "parent" in attrs else None
        parent_changed = "parent" in attrs and (not self.instance or parent != self.instance.parent)
        if parent_changed and parent and not parent.active:
            raise serializers.ValidationError({"parent": "Selecione um setor pai ativo."})
        effective_parent = parent if "parent" in attrs else getattr(self.instance, "parent", None)
        if effective_parent and unit and effective_parent.unit_id != unit.id:
            raise serializers.ValidationError({"parent": "O setor pai deve pertencer à mesma unidade."})
        if self.instance and unit_changed and unit and self.instance.children.exclude(unit=unit).exclude(unit__isnull=True).exists():
            raise serializers.ValidationError({"unit": "A unidade deve ser compatível com os setores filhos."})

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


class UserSectorMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    sector_code = serializers.CharField(source="sector.code", read_only=True, allow_null=True)

    class Meta:
        model = UserSectorMembership
        fields = ("id", "user", "user_name", "sector", "sector_name", "sector_code", "active", "is_primary", "is_manager", "created_at", "updated_at")
        read_only_fields = ("id", "user_name", "sector_name", "sector_code", "created_at", "updated_at")

    def create(self, validated_data):
        try:
            return save_membership(UserSectorMembership(**validated_data))
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        try:
            return save_membership(instance, **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
