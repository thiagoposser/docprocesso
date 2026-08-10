from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = ("id", "user", "user_name", "action", "action_display", "entity_type", "entity_id", "description", "old_values", "new_values", "ip_address", "user_agent", "request_method", "request_path", "created_at")
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "Sistema"
