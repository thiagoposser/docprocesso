from .models import AuditAction
from .services import record_audit, snapshot


class AuditedWriteMixin:
    audit_fields = ()
    audit_label = "registro"

    def perform_create(self, serializer):
        instance = self.save_audited_create(serializer)
        record_audit(action=AuditAction.CREATE, description=f"{self.audit_label.capitalize()} criado", request=self.request, entity=instance, new_values=snapshot(instance, self.audit_fields))

    def save_audited_create(self, serializer):
        return serializer.save()

    def perform_update(self, serializer):
        old_values = snapshot(serializer.instance, self.audit_fields)
        instance = serializer.save()
        new_values = snapshot(instance, self.audit_fields)
        if old_values.get("is_active", old_values.get("active")) is False and new_values.get("is_active", new_values.get("active")) is True:
            action = AuditAction.ACTIVATE
        elif old_values.get("is_active", old_values.get("active")) is True and new_values.get("is_active", new_values.get("active")) is False:
            action = AuditAction.DEACTIVATE
        else:
            action = AuditAction.UPDATE
        record_audit(action=action, description=f"{self.audit_label.capitalize()} atualizado", request=self.request, entity=instance, old_values=old_values, new_values=new_values)
