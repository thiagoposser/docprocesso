import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models


def logo_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"settings/logo-{uuid.uuid4().hex}{extension}"


def validate_logo(upload):
    extension = Path(upload.name).suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValidationError("Use uma imagem PNG, JPG ou WEBP.")
    if upload.size > 2 * 1024 * 1024:
        raise ValidationError("A logo deve ter no máximo 2 MB.")
    content_type = getattr(upload, "content_type", None)
    if content_type and content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValidationError("O tipo de conteúdo da logo não é permitido.")


class SystemSettings(models.Model):
    """Singleton containing only non-secret, user-facing configuration."""

    system_name = models.CharField(max_length=120, default="Base Admin")
    system_short_name = models.CharField(max_length=12, default="BA")
    system_description = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=30, default="0.1.0")
    logo = models.FileField(upload_to=logo_upload_path, validators=[validate_logo], blank=True)
    primary_color = models.CharField(max_length=7, default="#4a4ab8")
    timezone = models.CharField(max_length=64, default="America/Sao_Paulo")
    language_code = models.CharField(max_length=16, default="pt-br")
    support_email = models.EmailField(blank=True)
    support_url = models.URLField(blank=True)
    maintenance_mode = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [("generate_reports", "Pode gerar relatórios")]
        verbose_name = "configuração do sistema"
        verbose_name_plural = "configurações do sistema"

    def save(self, *args, **kwargs):
        if self._state.adding and SystemSettings.objects.filter(pk=1).exists():
            raise ValidationError("Já existe uma configuração principal.")
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("A configuração principal não pode ser excluída.")

    @classmethod
    def load(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    def __str__(self):
        return self.system_name
