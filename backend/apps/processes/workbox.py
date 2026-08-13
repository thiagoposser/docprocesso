from django.db.models import Q

from .models import ProcessStatus


WORKBOX_SCOPES = {"my-action", "my-sector", "created", "following", "completed"}


def apply_workbox_scope(queryset, *, user, scope):
    memberships = user.sector_memberships.effective()
    sector_ids = memberships.values_list("sector_id", flat=True)
    function_ids = memberships.exclude(function_id__isnull=True).values_list("function_id", flat=True)
    if scope == "my-action":
        if not user.is_superuser:
            transition_permission = Q()
            if user.has_perm("processes.forward_administrativeprocess"):
                transition_permission |= Q(current_stage__outgoing_transitions__is_return=False)
            if user.has_perm("processes.return_administrativeprocess"):
                transition_permission |= Q(current_stage__outgoing_transitions__is_return=True)
            if not transition_permission:
                return queryset.none()
            explicit = (
                Q(current_stage__outgoing_transitions__authorized_sector_id__isnull=False)
                | Q(current_stage__outgoing_transitions__authorized_function_id__isnull=False)
            )
            explicit &= (
                Q(current_stage__outgoing_transitions__authorized_sector_id__isnull=True)
                | Q(current_stage__outgoing_transitions__authorized_sector_id__in=sector_ids)
            ) & (
                Q(current_stage__outgoing_transitions__authorized_function_id__isnull=True)
                | Q(current_stage__outgoing_transitions__authorized_function_id__in=function_ids)
            )
            fallback = (
                Q(current_stage__outgoing_transitions__authorized_sector_id__isnull=True)
                & Q(current_stage__outgoing_transitions__authorized_function_id__isnull=True)
                & Q(responsible_sector_id__in=sector_ids)
                & (Q(responsible_function_id__isnull=True) | Q(responsible_function_id__in=function_ids))
            )
            queryset = queryset.filter(
                transition_permission, Q(current_stage__outgoing_transitions__active=True), explicit | fallback,
            )
        return queryset.exclude(
            status__in=[ProcessStatus.COMPLETED, ProcessStatus.CANCELLED, ProcessStatus.ARCHIVED]
        ).distinct()
    if scope == "my-sector":
        if user.is_superuser:
            return queryset.distinct()
        return queryset.filter(
            Q(current_sector_id__in=sector_ids)
            | Q(current_sector__isnull=True, origin_sector_id__in=sector_ids)
        ).distinct()
    if scope == "created":
        return queryset.filter(created_by=user).distinct()
    if scope == "following":
        return queryset.filter(Q(created_by=user) | Q(movements__actor=user)).distinct()
    return queryset.filter(status__in=[ProcessStatus.COMPLETED, ProcessStatus.ARCHIVED]).distinct()
