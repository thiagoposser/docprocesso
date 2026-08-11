from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Criação"
    UPDATE = "UPDATE", "Atualização"
    ACTIVATE = "ACTIVATE", "Ativação"
    DEACTIVATE = "DEACTIVATE", "Desativação"
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    LOGIN_FAILED = "LOGIN_FAILED", "Falha de login"
    PASSWORD_CHANGED = "PASSWORD_CHANGED", "Senha alterada"
    DOCUMENT_VIEW = "DOCUMENT_VIEW", "Documento visualizado"
    DOCUMENT_DOWNLOAD = "DOCUMENT_DOWNLOAD", "Documento baixado"
    SETTINGS_CHANGED = "SETTINGS_CHANGED", "Configurações alteradas"
    PROCESS_WORKFLOW = "PROCESS_WORKFLOW", "Tramitação de processo"
    PROCESS_EVENT = "PROCESS_EVENT", "Evento funcional de processo"
    PAYMENT_WORKFLOW = "PAYMENT_WORKFLOW", "Fluxo de pagamento"
    FILE_LIFECYCLE = "FILE_LIFECYCLE", "Ciclo de vida de arquivo"


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Registros de auditoria são imutáveis.")

    def delete(self):
        raise ValidationError("Registros de auditoria não podem ser excluídos.")


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=32, choices=AuditAction.choices, db_index=True)
    entity_type = models.CharField(max_length=100, blank=True, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True, db_index=True)
    description = models.CharField(max_length=500)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"

    def __str__(self):
        return f"{self.action} - {self.description}"

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("Registros de auditoria são imutáveis.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Registros de auditoria não podem ser excluídos.")
