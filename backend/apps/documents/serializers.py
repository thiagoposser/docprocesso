from pathlib import Path

from rest_framework import serializers

from .models import Document, DocumentCategory


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ("id", "name", "slug", "active", "created_at", "updated_at")
        read_only_fields = ("id", "slug", "created_at", "updated_at")


class DocumentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    source_type = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = (
            "id", "title", "description", "category", "category_name", "file", "file_url",
            "file_name", "file_size", "external_url", "source_type", "active", "created_by",
            "created_by_name", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_by_name", "file_url", "file_name", "file_size", "source_type", "created_at", "updated_at")
        extra_kwargs = {"file": {"write_only": True}}

    def validate(self, attrs):
        current_file = getattr(self.instance, "file", None)
        current_url = getattr(self.instance, "external_url", "")
        file_value = attrs.get("file", current_file)
        url_value = attrs.get("external_url", current_url)
        if bool(file_value) == bool(url_value):
            raise serializers.ValidationError("Informe um arquivo ou uma URL externa, mas não ambos.")
        return attrs

    def get_file_url(self, obj):
        if not obj.file:
            return None
        return f"/api/documents/{obj.pk}/download/"

    def get_file_name(self, obj):
        return obj.original_file_name or (Path(obj.file.name).name if obj.file else None)

    def get_file_size(self, obj):
        try:
            return obj.file.size if obj.file else None
        except OSError:
            return None

    def create(self, validated_data):
        upload = validated_data.get("file")
        if upload:
            validated_data["original_file_name"] = Path(upload.name).name[:255]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        upload = validated_data.get("file")
        if upload:
            validated_data["original_file_name"] = Path(upload.name).name[:255]
        return super().update(instance, validated_data)
