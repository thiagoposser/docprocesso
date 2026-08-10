from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def configure_document_permissions(sender, **kwargs):
    if sender.label != "documents":
        return
    administrator, _ = Group.objects.get_or_create(name="Administrador")
    permission = Permission.objects.filter(content_type__app_label="documents", codename="manage_document").first()
    if permission:
        administrator.permissions.add(permission)
