from datetime import timedelta

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
    from apps.processes.workbox import apply_workbox_scope

    scoped = apply_workbox_scope(AdministrativeProcess.objects.all(), user=user, scope="my-sector")
    counts = scoped.aggregate(
        in_progress=Count("id", filter=Q(status__in=(ProcessStatus.OPEN, ProcessStatus.IN_PROGRESS))),
        completed=Count("id", filter=Q(status=ProcessStatus.COMPLETED)),
        total=Count("id"),
    )
    my_action = apply_workbox_scope(scoped, user=user, scope="my-action")
    stalled_days = 7
    counts.update({
        "my_action": my_action.count(),
        "awaiting_approval": my_action.filter(
            Q(current_stage__outgoing_transitions__code__icontains="aprova")
            | Q(current_stage__outgoing_transitions__name__icontains="aprova")
        ).distinct().count(),
        "my_sector": scoped.exclude(
            status__in=(ProcessStatus.COMPLETED, ProcessStatus.CANCELLED, ProcessStatus.ARCHIVED)
        ).count(),
        "stalled": scoped.filter(
            status__in=(ProcessStatus.OPEN, ProcessStatus.IN_PROGRESS),
            updated_at__lt=timezone.now() - timedelta(days=stalled_days),
        ).count(),
        "stalled_days": stalled_days,
        "as_of": timezone.now(),
        "by_stage": list(
            scoped.exclude(current_stage__isnull=True)
            .values("current_stage_id", "current_stage__name")
            .annotate(count=Count("id")).order_by("current_stage__order", "current_stage_id")
        ),
    })
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
        scheduled=Count("id", filter=Q(status=PaymentStatus.SCHEDULED)),
        overdue=Count("id", filter=Q(due_date__lt=today)),
        due_this_month=Count("id", filter=Q(due_date__year=today.year, due_date__month=today.month)),
        due_next_7_days=Count("id", filter=Q(due_date__range=(today, today + timedelta(days=7)))),
        pending_total=Sum("amount"),
    )
    totals["pending_total"] = str(totals["pending_total"] or 0)
    totals["as_of"] = timezone.now()
    return totals
