from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone


def dashboard_summary(user=None):
    User = get_user_model()
    from apps.documents.models import Document, DocumentRole
    summary = {
        "total_users": User.objects.filter(is_active=True).count(),
        "total_documents": Document.objects.filter(active=True).exclude(role=DocumentRole.PAYMENT_RECEIPT).count(),
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


def _sector_ids(user):
    if user.is_superuser:
        return None
    return user.sector_memberships.effective().values_list("sector_id", flat=True)


def process_dashboard_summary(user):
    from apps.processes.models import AdministrativeProcess, ProcessStatus

    queryset = AdministrativeProcess.objects.all()
    sector_ids = _sector_ids(user)
    if sector_ids is not None:
        queryset = queryset.filter(current_sector_id__in=sector_ids)
    counts = queryset.aggregate(
        in_progress=Count("id", filter=Q(status__in=(ProcessStatus.OPEN, ProcessStatus.IN_PROGRESS))),
        completed=Count("id", filter=Q(status=ProcessStatus.COMPLETED)),
        total=Count("id"),
    )
    return counts


def financial_dashboard_summary(user):
    from apps.payments.models import Payment, PaymentStatus

    today = timezone.localdate()
    queryset = Payment.objects.filter(status__in=(PaymentStatus.PENDING, PaymentStatus.SCHEDULED))
    sector_ids = _sector_ids(user)
    if sector_ids is not None:
        queryset = queryset.filter(sector_id__in=sector_ids)
    totals = queryset.aggregate(
        pending=Count("id"),
        overdue=Count("id", filter=Q(due_date__lt=today)),
        due_this_month=Count("id", filter=Q(due_date__year=today.year, due_date__month=today.month)),
        pending_total=Sum("amount"),
    )
    totals["pending_total"] = str(totals["pending_total"] or 0)
    return totals
