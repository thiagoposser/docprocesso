from django.conf import settings
from django.contrib.auth import get_user_model


def dashboard_summary(user=None):
    User = get_user_model()
    from apps.documents.models import Document
    summary = {
        "total_users": User.objects.filter(is_active=True).count(),
        "total_documents": Document.objects.filter(active=True).count(),
        "api_status": "operational",
        "environment": settings.ENVIRONMENT,
        "version": settings.API_VERSION,
    }
    if user and user.has_perm("audit.view_auditlog"):
        from apps.audit.models import AuditLog
        summary["recent_activity"] = [
            {"id": log.id, "action": log.get_action_display(), "description": log.description, "user": log.user.full_name if log.user else "Sistema", "created_at": log.created_at}
            for log in AuditLog.objects.select_related("user")[:5]
        ]
    return summary
