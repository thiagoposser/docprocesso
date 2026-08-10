from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .services.group_service import ensure_default_groups


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    if sender.label == "users":
        ensure_default_groups()
