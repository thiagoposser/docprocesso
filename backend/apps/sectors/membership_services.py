from django.db import transaction
from django.utils import timezone

from .models import UserSectorMembership


@transaction.atomic
def save_membership(membership, **changes):
    for field, value in changes.items():
        setattr(membership, field, value)
    if membership.active and membership.is_primary:
        UserSectorMembership.objects.select_for_update().filter(
            user=membership.user,
            active=True,
            is_primary=True,
        ).exclude(pk=membership.pk).update(is_primary=False, updated_at=timezone.now())
    membership.save()
    return membership
