from django.contrib import admin

from .models import Attachment, Document, DocumentCategory


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "slug")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "process", "role", "active", "created_by", "updated_at")
    list_filter = ("active", "category", "process", "role")
    search_fields = ("title", "description", "category__name", "process__number")
    autocomplete_fields = ("process",)
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("document", "source_type", "active", "created_by", "created_at", "deactivated_at")
    list_filter = ("active", "created_at")
    search_fields = ("document__title", "document__process__number", "original_file_name", "external_url")
    autocomplete_fields = ("document", "created_by")
    readonly_fields = ("created_at", "deactivated_at")

    def has_delete_permission(self, request, obj=None):
        return False
