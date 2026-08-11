from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Sector(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=30, unique=True, blank=True, null=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        blank=True,
        null=True,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_sectors",
        blank=True,
        null=True,
    )
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        default_permissions = ("add", "change", "view")
        permissions = [("manage_sector", "Pode gerenciar setores")]
        indexes = [
            models.Index(fields=["parent", "active"], name="sector_parent_active_idx"),
        ]
        verbose_name = "setor"
        verbose_name_plural = "setores"

    def clean(self):
        super().clean()
        if self.code == "":
            self.code = None
        if self.parent_id is None:
            return
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({"parent": "Um setor não pode ser pai de si mesmo."})

        ancestor_id = self.parent_id
        visited = set()
        while ancestor_id:
            if ancestor_id == self.pk or ancestor_id in visited:
                raise ValidationError({"parent": "A hierarquia de setores não pode conter ciclos."})
            visited.add(ancestor_id)
            ancestor_id = (
                Sector.objects.filter(pk=ancestor_id)
                .values_list("parent_id", flat=True)
                .first()
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}" if self.code else self.name
