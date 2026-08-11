from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class NotificationType(models.TextChoices):
    SYSTEM = "SYSTEM", "Sistema"
    USER = "USER", "Usuário"
    DOCUMENT = "DOCUMENT", "Documento"
    SECURITY = "SECURITY", "Segurança"
    ADMIN = "ADMIN", "Administração"
    PAYMENT = "PAYMENT", "Pagamento"


class NotificationLevel(models.TextChoices):
    INFO = "INFO", "Informação"
    SUCCESS = "SUCCESS", "Sucesso"
    WARNING = "WARNING", "Atenção"
    ERROR = "ERROR", "Erro"


def validate_action_url(value):
    if not value:
        return
    if value.startswith("/") and not value.startswith("//"):
        return
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("Use uma rota interna ou URL HTTP/HTTPS segura.")


class NotificationQuerySet(models.QuerySet):
    def available(self):
        from django.utils import timezone
        return self.filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now()))


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=160)
    message = models.CharField(max_length=500)
    type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    level = models.CharField(max_length=20, choices=NotificationLevel.choices, default=NotificationLevel.INFO)
    action_url = models.CharField(max_length=1000, blank=True, validators=[validate_action_url])
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    deduplication_key = models.CharField(max_length=160, blank=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "read", "created_at"], name="notif_user_read_created"),
            models.Index(fields=["user", "type", "created_at"], name="notif_user_type_created"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "deduplication_key"], condition=~models.Q(deduplication_key=""),
                name="unique_user_notification_dedupe",
            ),
        ]

    def __str__(self):
        return f"{self.user}: {self.title}"
