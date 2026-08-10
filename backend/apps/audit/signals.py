from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def configure_audit_permissions(sender, **kwargs):
    if sender.label != "audit":
        return
    administrator, _ = Group.objects.get_or_create(name="Administrador")
    permission = Permission.objects.filter(content_type__app_label="audit", codename="view_auditlog").first()
    if permission:
        administrator.permissions.add(permission)
