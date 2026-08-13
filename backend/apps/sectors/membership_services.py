from django.db import transaction
from django.utils import timezone

from .models import UserSectorMembership


@transaction.atomic
def save_membership(membership, **changes):
    for field, value in changes.items():
        setattr(membership, field, value)
    was_primary = membership.is_primary
    if not membership.active:
        membership.is_primary = False
    current_date = timezone.localdate()
    is_effective = (
        membership.active
        and membership.starts_on <= current_date
        and (membership.ends_on is None or membership.ends_on >= current_date)
    )
    has_effective_primary = UserSectorMembership.objects.effective(current_date).filter(
        user=membership.user,
        is_primary=True,
    ).exclude(pk=membership.pk).exists()
    if is_effective and not has_effective_primary:
        membership.is_primary = True
    if membership.active and membership.is_primary:
        UserSectorMembership.objects.select_for_update().filter(
            user=membership.user,
            active=True,
            is_primary=True,
        ).exclude(pk=membership.pk).update(is_primary=False, updated_at=timezone.now())
    membership.save()
    if not membership.active and was_primary:
        replacement_id = UserSectorMembership.objects.effective(current_date).filter(
            user=membership.user,
        ).exclude(pk=membership.pk).order_by("starts_on", "pk").values_list("pk", flat=True).first()
        if replacement_id:
            replacement = UserSectorMembership.objects.select_for_update().get(pk=replacement_id)
            replacement.is_primary = True
            replacement.save(update_fields=["is_primary", "updated_at"])
    return membership
