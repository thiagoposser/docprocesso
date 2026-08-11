from django.contrib import admin

from .models import AdministrativeProcess, ProcessMovement, ProcessType


@admin.register(ProcessType)
class ProcessTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "code")
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AdministrativeProcess)
class AdministrativeProcessAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "process_type", "status", "current_sector", "assignee", "updated_at")
    list_filter = ("status", "process_type", "origin_sector", "current_sector")
    search_fields = ("number", "title", "description")
    autocomplete_fields = ("process_type", "created_by", "origin_sector", "current_sector", "assignee")
    readonly_fields = ("number", "version", "created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProcessMovement)
class ProcessMovementAdmin(admin.ModelAdmin):
    list_display = ("process", "action", "from_sector", "to_sector", "actor", "created_at")
    list_filter = ("action", "from_sector", "to_sector")
    search_fields = ("process__number", "process__title", "actor__username", "note")
    readonly_fields = (
        "process", "action", "from_sector", "to_sector", "actor", "note",
        "status_before", "status_after", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
