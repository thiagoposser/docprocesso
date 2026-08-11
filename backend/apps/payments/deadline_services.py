from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.notifications.models import Notification, NotificationLevel, NotificationType
from apps.notifications.services import NotificationService

from .models import Payment, PaymentStatus


DEADLINE_BUCKETS = ("overdue", "today", "upcoming")


def classify_deadline(due_date, *, as_of=None, upcoming_days=7):
    as_of = as_of or timezone.localdate()
    if due_date < as_of:
        return "overdue"
    if due_date == as_of:
        return "today"
    if due_date <= as_of + timedelta(days=upcoming_days):
        return "upcoming"
    return None


def _expires_at(bucket, due_date, as_of):
    expiration_date = due_date if bucket == "upcoming" else as_of + timedelta(days=1)
    return timezone.make_aware(
        datetime.combine(expiration_date, time.min), timezone.get_current_timezone(),
    )


def _eligible_users(payment, user=None):
    users = get_user_model().objects.filter(is_active=True)
    if user is not None:
        users = users.filter(pk=user.pk)
    users = users.filter(
        Q(is_superuser=True)
        | Q(
            sector_memberships__sector=payment.sector,
            sector_memberships__active=True,
        )
    ).distinct()
    required = (
        "payments.view_payment", "payments.view_financial_data",
        "processes.view_administrativeprocess",
    )
    return [candidate for candidate in users if candidate.has_perms(required)]


def generate_deadline_notifications(*, user=None, as_of=None, upcoming_days=7):
    as_of = as_of or timezone.localdate()
    generated = []
    payments = Payment.objects.filter(
        status__in=(PaymentStatus.PENDING, PaymentStatus.SCHEDULED),
        due_date__lte=as_of + timedelta(days=upcoming_days),
    ).select_related("sector")
    for payment in payments:
        bucket = classify_deadline(payment.due_date, as_of=as_of, upcoming_days=upcoming_days)
        if not bucket:
            continue
        for recipient in _eligible_users(payment, user=user):
            prefix = f"payment:{payment.pk}:deadline:"
            Notification.objects.filter(
                user=recipient, deduplication_key__startswith=prefix,
            ).exclude(deduplication_key=f"{prefix}{bucket}").update(expires_at=timezone.now())
            labels = {
                "overdue": ("Pagamento vencido", "Há um pagamento vencido que requer atenção.", NotificationLevel.ERROR),
                "today": ("Pagamento vence hoje", "Há um pagamento com vencimento hoje.", NotificationLevel.WARNING),
                "upcoming": ("Pagamento próximo do vencimento", "Há um pagamento com vencimento próximo.", NotificationLevel.INFO),
            }
            title, message, level = labels[bucket]
            notification, _ = NotificationService.create_once(
                user=recipient, deduplication_key=f"{prefix}{bucket}",
                title=title, message=message, type=NotificationType.PAYMENT,
                level=level, action_url=f"/pagamentos/{payment.pk}",
                expires_at=_expires_at(bucket, payment.due_date, as_of),
            )
            generated.append(notification)
    return generated
