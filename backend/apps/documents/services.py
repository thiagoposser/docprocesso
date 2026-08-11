from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.processes.event_services import append_process_event
from apps.processes.models import ProcessEventType

from .models import Attachment, Document, safe_original_filename


@transaction.atomic
def create_process_document(*, process, actor, request=None, **data):
    document = Document.objects.create(process=process, created_by=actor, **data)
    record_audit(
        action=AuditAction.CREATE, description="Documento do processo criado", request=request,
        entity=document, new_values={"process_id": process.pk, "title": document.title},
    )
    append_process_event(
        process=process, event_type=ProcessEventType.DOCUMENT_CHANGED,
        title="Documento incluído", actor=actor,
        payload={"document_id": document.pk, "title": document.title},
    )
    return document


@transaction.atomic
def create_attachment(*, document, actor, request=None, **data):
    upload = data.get("file")
    if upload:
        data["original_file_name"] = safe_original_filename(upload.name)
    attachment = Attachment.objects.create(document=document, created_by=actor, **data)
    record_audit(
        action=AuditAction.CREATE, description="Anexo criado", request=request, entity=attachment,
        new_values={"document_id": document.pk, "source_type": attachment.source_type},
    )
    if document.process_id:
        append_process_event(
            process=document.process, event_type=ProcessEventType.DOCUMENT_CHANGED,
            title="Anexo incluído", actor=actor,
            payload={"document_id": document.pk, "attachment_id": attachment.pk},
        )
    return attachment


@transaction.atomic
def deactivate_attachment(*, attachment, actor, request=None):
    if attachment.active:
        attachment.active = False
        attachment.deactivated_at = timezone.now()
        attachment.save(update_fields=("active", "deactivated_at"))
        record_audit(
            action=AuditAction.DEACTIVATE, description="Anexo desativado", request=request,
            entity=attachment, old_values={"active": True}, new_values={"active": False},
        )
        if attachment.document.process_id:
            append_process_event(
                process=attachment.document.process, event_type=ProcessEventType.DOCUMENT_CHANGED,
                title="Anexo desativado", actor=actor,
                payload={"document_id": attachment.document_id, "attachment_id": attachment.pk},
            )
    return attachment
