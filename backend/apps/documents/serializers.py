from pathlib import Path

from rest_framework import serializers

from .models import Attachment, Document, DocumentCategory, safe_original_filename, validate_document_file


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
            "id", "process", "title", "description", "category", "category_name", "file", "file_url",
            "file_name", "file_size", "external_url", "source_type", "active", "created_by",
            "created_by_name", "created_at", "updated_at",
        )
        read_only_fields = ("id", "process", "created_by", "created_by_name", "file_url", "file_name", "file_size", "source_type", "created_at", "updated_at")
        extra_kwargs = {"file": {"write_only": True}}

    def validate(self, attrs):
        current_file = getattr(self.instance, "file", None)
        current_url = getattr(self.instance, "external_url", "")
        file_value = attrs.get("file", current_file)
        url_value = attrs.get("external_url", current_url)
        process_id = getattr(self.instance, "process_id", None)
        if bool(file_value) == bool(url_value) and (file_value or url_value or not process_id):
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
            validated_data["original_file_name"] = safe_original_filename(upload.name)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        upload = validated_data.get("file")
        if upload:
            validated_data["original_file_name"] = safe_original_filename(upload.name)
        return super().update(instance, validated_data)


class AttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False, validators=[validate_document_file])
    external_url = serializers.URLField(write_only=True, required=False)
    file_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    source_type = serializers.CharField(read_only=True)

    class Meta:
        model = Attachment
        fields = (
            "id", "document", "file", "external_url", "file_name", "download_url",
            "source_type", "active", "created_by", "created_at", "deactivated_at",
        )
        read_only_fields = (
            "id", "document", "file_name", "download_url", "source_type", "active",
            "created_by", "created_at", "deactivated_at",
        )

    def validate(self, attrs):
        if bool(attrs.get("file")) == bool(attrs.get("external_url")):
            raise serializers.ValidationError("Informe um arquivo ou uma URL externa, mas não ambos.")
        return attrs

    def get_file_name(self, obj):
        return obj.original_file_name or (Path(obj.file.name).name if obj.file else None)

    def get_download_url(self, obj):
        return f"/api/attachments/{obj.pk}/download/" if obj.active else None


class ProcessDocumentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = (
            "id", "process", "title", "description", "category", "category_name", "active",
            "created_by", "created_by_name", "created_at", "updated_at", "attachments",
        )
        read_only_fields = (
            "id", "process", "created_by", "created_by_name", "created_at", "updated_at", "attachments",
        )
