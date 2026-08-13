from dataclasses import dataclass

from .models import Sector, UserSectorMembership


@dataclass(frozen=True)
class SectorAccessDecision:
    allowed: bool
    reason: str


def evaluate_sector_access(user, *, permission, sector, resource_state=None, allowed_states=None, require_manager=False):
    if not getattr(user, "is_authenticated", False):
        return SectorAccessDecision(False, "authentication_required")
    if user.is_superuser:
        return SectorAccessDecision(True, "superuser")
    if not user.has_perm(permission):
        return SectorAccessDecision(False, "permission_required")
    if not isinstance(sector, Sector) or not sector.active:
        return SectorAccessDecision(False, "inactive_or_invalid_sector")
    if allowed_states is not None and resource_state not in set(allowed_states):
        return SectorAccessDecision(False, "invalid_resource_state")
    membership = UserSectorMembership.objects.effective().filter(user=user, sector=sector).only("is_manager").first()
    if not membership:
        return SectorAccessDecision(False, "sector_membership_required")
    if require_manager and not membership.is_manager:
        return SectorAccessDecision(False, "sector_manager_required")
    return SectorAccessDecision(True, "allowed")


def can_access_sector(user, **kwargs):
    return evaluate_sector_access(user, **kwargs).allowed
