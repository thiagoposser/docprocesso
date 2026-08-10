from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "title", "type", "level", "read", "expires_at")
    list_filter = ("type", "level", "read")
    search_fields = ("title", "message", "user__username")
    readonly_fields = ("read_at", "created_at")
