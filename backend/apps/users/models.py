from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extensible project user while retaining Django's proven auth fields."""

    photo = models.ImageField(upload_to="users/photos/%Y/%m/", blank=True, null=True)

    # Keeping this table preserves existing template users and group relations.
    class Meta(AbstractUser.Meta):
        db_table = "auth_user"
        ordering = ["first_name", "last_name", "username"]

    @property
    def full_name(self):
        return self.get_full_name() or self.username
