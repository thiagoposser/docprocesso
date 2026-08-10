from django.contrib.auth.models import Group


DEFAULT_GROUPS = ("Administrador", "Usuário")


def ensure_default_groups():
    for name in DEFAULT_GROUPS:
        Group.objects.get_or_create(name=name)
