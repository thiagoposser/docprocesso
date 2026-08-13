from django.contrib import admin

from .models import OrganizationalFunction, OrganizationalUnit, Sector, UserSectorMembership


@admin.register(OrganizationalFunction)
class OrganizationalFunctionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "acronym", "parent", "active", "updated_at")
    list_filter = ("active", "parent")
    search_fields = ("name", "acronym", "description")
    autocomplete_fields = ("parent",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "unit", "parent", "manager", "active", "updated_at")
    list_filter = ("active", "unit", "parent")
    search_fields = ("name", "code", "unit__name", "unit__acronym", "manager__username", "manager__first_name", "manager__last_name")
    autocomplete_fields = ("unit", "parent", "manager")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserSectorMembership)
class UserSectorMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "unit", "sector", "function", "active", "is_primary", "starts_on", "ends_on", "updated_at")
    list_filter = ("active", "is_primary", "is_manager", "unit", "sector", "function")
    search_fields = ("user__username", "user__first_name", "user__last_name", "unit__name", "sector__name", "sector__code", "function__name", "function__code")
    autocomplete_fields = ("user", "unit", "sector", "function")
    readonly_fields = ("created_at", "updated_at")
