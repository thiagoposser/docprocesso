from django.contrib import admin

from .models import Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "parent", "manager", "active", "updated_at")
    list_filter = ("active", "parent")
    search_fields = ("name", "code", "manager__username", "manager__first_name", "manager__last_name")
    autocomplete_fields = ("parent", "manager")
    readonly_fields = ("created_at", "updated_at")
