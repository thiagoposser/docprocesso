from django.db import transaction

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.processes.event_services import append_process_event
from apps.processes.models import ProcessEventType, ProcessStatus
from apps.sectors.policies import evaluate_sector_access

from .models import Payment, PaymentReceipt, PaymentStatus


class PaymentDomainError(Exception):
    pass


class PaymentConflictError(PaymentDomainError):
    pass


class InvalidPaymentTransition(PaymentDomainError):
    pass


class PaymentAccessDenied(PaymentDomainError):
    pass


ACTION_PERMISSIONS = {
    "schedule": "payments.schedule_payment",
    "confirm": "payments.confirm_payment",
    "cancel": "payments.cancel_payment",
}


def _require_action_access(actor, payment, action):
    decision = evaluate_sector_access(actor, permission=ACTION_PERMISSIONS[action], sector=payment.sector)
    if not decision.allowed or not actor.has_perm("payments.view_financial_data") or not actor.has_perm("processes.view_administrativeprocess"):
        raise PaymentAccessDenied(f"Ação financeira não permitida: {decision.reason}.")
    if payment.process.status in {ProcessStatus.CANCELLED, ProcessStatus.ARCHIVED}:
        raise InvalidPaymentTransition("Não é possível alterar pagamentos de processo cancelado ou arquivado.")


@transaction.atomic
def _perform_payment_action(*, payment_id, actor, action, **values):
    payment = Payment.objects.select_for_update(of=("self",)).select_related("sector", "process").get(pk=payment_id)
    _require_action_access(actor, payment, action)
    allowed = {
        "schedule": {PaymentStatus.PENDING},
        "confirm": {PaymentStatus.PENDING, PaymentStatus.SCHEDULED},
        "cancel": {PaymentStatus.PENDING, PaymentStatus.SCHEDULED},
    }[action]
    if payment.status not in allowed:
        raise PaymentConflictError(f"O pagamento já está no estado {payment.status}.")
    before = payment.status
    if action == "schedule":
        payment.status = PaymentStatus.SCHEDULED
        payment.scheduled_at = values["scheduled_at"]
        title = "Pagamento agendado"
    elif action == "confirm":
        payment.status = PaymentStatus.PAID
        payment.paid_at = values["paid_at"]
        payment.paid_amount = values["paid_amount"]
        payment.payment_method = values["payment_method"]
        payment.paid_by = actor
        title = "Pagamento confirmado"
    else:
        from django.utils import timezone
        payment.status = PaymentStatus.CANCELLED
        payment.cancelled_at = timezone.now()
        payment.cancellation_reason = values["reason"]
        title = "Pagamento cancelado"
    payment.save()
    record_audit(
        action=AuditAction.UPDATE, description=title, user=actor, entity=payment,
        old_values={"status": before}, new_values={"status": payment.status},
    )
    append_process_event(
        process=payment.process, event_type=ProcessEventType.PAYMENT_CHANGED,
        title=title, actor=actor,
        description=values.get("reason", ""),
        payload={"payment_id": payment.pk, "status_before": before, "status_after": payment.status},
    )
    return payment


def schedule_payment(*, payment_id, actor, scheduled_at):
    return _perform_payment_action(payment_id=payment_id, actor=actor, action="schedule", scheduled_at=scheduled_at)


def confirm_payment(*, payment_id, actor, paid_at, paid_amount, payment_method):
    return _perform_payment_action(
        payment_id=payment_id, actor=actor, action="confirm",
        paid_at=paid_at, paid_amount=paid_amount, payment_method=payment_method,
    )


def cancel_payment(*, payment_id, actor, reason):
    return _perform_payment_action(payment_id=payment_id, actor=actor, action="cancel", reason=reason)


@transaction.atomic
def create_payment_receipt(*, payment_id, actor, upload, request=None):
    from pathlib import Path
    from apps.documents.models import Attachment, Document, DocumentCategory, DocumentRole

    payment = Payment.objects.select_for_update(of=("self",)).select_related("process", "sector").get(pk=payment_id)
    decision = evaluate_sector_access(actor, permission="payments.manage_payment_receipt", sector=payment.sector)
    if not decision.allowed or not actor.has_perm("payments.view_financial_data"):
        raise PaymentAccessDenied(f"Comprovante não permitido: {decision.reason}.")
    if payment.status != PaymentStatus.PAID:
        raise InvalidPaymentTransition("Comprovantes só podem ser anexados a pagamentos confirmados.")
    if payment.process.status in {ProcessStatus.CANCELLED, ProcessStatus.ARCHIVED}:
        raise InvalidPaymentTransition("Não é possível anexar comprovante a processo cancelado ou arquivado.")
    category, _ = DocumentCategory.objects.get_or_create(name="Comprovantes de pagamento")
    document = Document.objects.create(
        title=f"Comprovante do pagamento {payment.pk}", category=category,
        process=payment.process, role=DocumentRole.PAYMENT_RECEIPT, created_by=actor,
    )
    attachment = Attachment.objects.create(
        document=document, file=upload, original_file_name=Path(upload.name).name[:255], created_by=actor,
    )
    receipt = PaymentReceipt.objects.create(payment=payment, attachment=attachment, created_by=actor)
    record_audit(
        action=AuditAction.CREATE, description="Comprovante de pagamento anexado", request=request,
        entity=receipt, new_values={"payment_id": payment.pk, "attachment_id": attachment.pk},
    )
    append_process_event(
        process=payment.process, event_type=ProcessEventType.PAYMENT_CHANGED,
        title="Comprovante anexado", actor=actor,
        payload={"payment_id": payment.pk, "receipt_id": receipt.pk, "attachment_id": attachment.pk},
    )
    return receipt


@transaction.atomic
def save_supplier(instance, **values):
    for field, value in values.items():
        setattr(instance, field, value)
    instance.save()
    return instance


@transaction.atomic
def save_payment(instance, **values):
    for field, value in values.items():
        setattr(instance, field, value)
    instance.save()
    return instance
