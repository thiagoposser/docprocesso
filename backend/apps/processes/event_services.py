import json
from collections.abc import Mapping

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditAction
from apps.audit.services import record_audit

from .models import ProcessEvent, ProcessEventType

SENSITIVE_EVENT_PARTS = (
    "password", "token", "secret", "authorization", "cookie", "credential",
    "database_url", "redis_url", "file_content", "content", "binary", "base64",
    "bank", "account", "card", "pix", "amount", "value", "price",
)
MAX_EVENT_PAYLOAD_BYTES = 8 * 1024
MAX_EVENT_STRING_LENGTH = 500
MAX_EVENT_COLLECTION_ITEMS = 50
MAX_EVENT_DEPTH = 4


def sanitize_event_payload(value, *, depth=0):
    if depth >= MAX_EVENT_DEPTH:
        return "[limitado]"
    if isinstance(value, Mapping):
        result = {}
        for key, item in list(value.items())[:MAX_EVENT_COLLECTION_ITEMS]:
            key = str(key)[:100]
            if any(part in key.lower() for part in SENSITIVE_EVENT_PARTS):
                continue
            result[key] = sanitize_event_payload(item, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple, set)):
        return [sanitize_event_payload(item, depth=depth + 1) for item in list(value)[:MAX_EVENT_COLLECTION_ITEMS]]
    if isinstance(value, str):
        return value[:MAX_EVENT_STRING_LENGTH]
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)[:MAX_EVENT_STRING_LENGTH]


def _validated_payload(payload):
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise ValidationError({"payload": "O payload do evento deve ser um objeto JSON."})
    sanitized = sanitize_event_payload(payload)
    encoded = json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_EVENT_PAYLOAD_BYTES:
        raise ValidationError({"payload": "O payload sanitizado excede o limite de 8 KB."})
    return sanitized


@transaction.atomic
def append_process_event(
    *, process, event_type, title, actor=None, description="", payload=None, corrects_event=None
):
    if event_type == ProcessEventType.CORRECTION:
        if corrects_event is None or corrects_event.process_id != process.pk:
            raise ValidationError({"corrects_event": "Informe um evento do mesmo processo a ser corrigido."})
        payload = {**(payload or {}), "corrects_event_id": corrects_event.pk}
    clean_payload = _validated_payload(payload)
    event = ProcessEvent.objects.create(
        process=process,
        event_type=event_type,
        title=title[:200],
        description=description[:2000],
        actor=actor,
        payload=clean_payload,
    )
    record_audit(
        action=AuditAction.PROCESS_EVENT,
        description=f"Evento funcional registrado: {event.title}",
        user=actor,
        entity=process,
        new_values={"event_id": event.pk, "event_type": event.event_type, "payload": clean_payload},
    )
    return event
