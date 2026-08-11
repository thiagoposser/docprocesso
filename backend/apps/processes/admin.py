from django.contrib import admin

from .models import AdministrativeProcess, ProcessType


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
