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


class UserSectorMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sector_memberships",
    )
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="user_memberships",
    )
    active = models.BooleanField(default=True, db_index=True)
    is_primary = models.BooleanField(default=False)
    is_manager = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id", "-is_primary", "sector__name"]
        default_permissions = ("add", "change", "view")
        permissions = [("manage_user_sector_membership", "Pode gerenciar vínculos entre usuários e setores")]
        constraints = [
            models.UniqueConstraint(fields=["user", "sector"], name="unique_user_sector_membership"),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(active=True, is_primary=True),
                name="unique_active_primary_sector_per_user",
            ),
            models.CheckConstraint(
                condition=models.Q(is_primary=False) | models.Q(active=True),
                name="primary_membership_must_be_active",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "active"], name="membership_user_active_idx"),
            models.Index(fields=["sector", "active"], name="membership_sector_active_idx"),
        ]
        verbose_name = "vínculo de usuário com setor"
        verbose_name_plural = "vínculos de usuários com setores"

    def clean(self):
        super().clean()
        if self.is_primary and not self.active:
            raise ValidationError({"is_primary": "O setor principal deve estar ativo."})
        activating = self.active
        if self.pk:
            previous_active = UserSectorMembership.objects.filter(pk=self.pk).values_list("active", flat=True).first()
            activating = previous_active is False and self.active
        if activating and self.user_id and not self.user.is_active:
            raise ValidationError({"user": "Não é possível vincular um usuário inativo."})
        if activating and self.sector_id and not self.sector.active:
            raise ValidationError({"sector": "Não é possível vincular um setor inativo."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} — {self.sector}"
