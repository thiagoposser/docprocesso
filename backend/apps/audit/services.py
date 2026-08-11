from collections.abc import Mapping

from .models import AuditLog

SENSITIVE_PARTS = (
    "password", "token", "secret", "authorization", "cookie", "credential",
    "database_url", "redis_url", "bank", "account", "agency", "branch",
    "card", "pix", "tax_id", "file_content", "binary", "base64",
)


def sanitize(value):
    if isinstance(value, Mapping):
        return {
            str(key): sanitize(item)
            for key, item in value.items()
            if not any(part in str(key).lower() for part in SENSITIVE_PARTS)
        }
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def request_metadata(request):
    if not request:
        return {}
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return {
        "ip_address": forwarded or request.META.get("REMOTE_ADDR") or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
        "request_method": request.method[:10],
        "request_path": request.path[:500],
    }


def record_audit(*, action, description, request=None, user=None, entity=None, entity_type="", entity_id="", old_values=None, new_values=None):
    actor = user or (getattr(request, "user", None) if request else None)
    if not getattr(actor, "is_authenticated", False):
        actor = None
    if entity is not None:
        entity_type = entity._meta.label
        entity_id = str(entity.pk or "")
    return AuditLog.objects.create(
        user=actor, action=action, entity_type=entity_type, entity_id=entity_id,
        description=description[:500], old_values=sanitize(old_values or {}),
        new_values=sanitize(new_values or {}), **request_metadata(request),
    )


def snapshot(instance, fields):
    values = {}
    for field in fields:
        if field in {"groups", "user_permissions"}:
            manager = getattr(instance, field)
            values[field] = sorted(manager.values_list("name" if field == "groups" else "codename", flat=True)) if instance.pk else []
        else:
            value = getattr(instance, field, None)
            values[field] = value.pk if hasattr(value, "pk") else value
    return sanitize(values)
