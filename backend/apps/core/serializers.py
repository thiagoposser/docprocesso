import re

from rest_framework import serializers

from .models import SystemSettings


class PublicSettingsSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = SystemSettings
        fields = ("system_name", "system_short_name", "logo_url", "primary_color", "language_code", "timezone", "version")

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None


class AdminSettingsSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = SystemSettings
        fields = (
            "system_name", "system_short_name", "system_description", "version", "logo", "logo_url",
            "primary_color", "timezone", "language_code", "support_email", "support_url",
            "maintenance_mode", "created_at", "updated_at",
        )
        read_only_fields = ("logo_url", "created_at", "updated_at")
        extra_kwargs = {"logo": {"write_only": True, "required": False}}

    def validate_primary_color(self, value):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise serializers.ValidationError("Use uma cor hexadecimal no formato #RRGGBB.")
        return value.lower()

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None
