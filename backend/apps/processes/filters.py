import re

from django.db.models import Q
from rest_framework import filters
from rest_framework.exceptions import ValidationError


class OperationalProcessSearchFilter(filters.BaseFilterBackend):
    """Bounded operational search; sector scope is applied by the view first."""

    def filter_queryset(self, request, queryset, view):
        term = request.query_params.get("search", "").strip()
        if not term:
            return queryset
        if len(term) > 100:
            raise ValidationError({"search": "A busca deve possuir no máximo 100 caracteres."})
        query = (
            Q(number__icontains=term) | Q(title__icontains=term) | Q(description__icontains=term)
            | Q(process_type__name__icontains=term) | Q(current_sector__name__icontains=term)
            | Q(current_sector__code__icontains=term) | Q(origin_sector__name__icontains=term)
            | Q(current_stage__name__icontains=term) | Q(responsible_sector__name__icontains=term)
            | Q(responsible_function__name__icontains=term) | Q(responsible_sector__unit__name__icontains=term)
            | Q(assignee__username__icontains=term) | Q(assignee__first_name__icontains=term)
            | Q(assignee__last_name__icontains=term) | Q(status__icontains=term)
            | Q(movements__note__icontains=term) | Q(events__title__icontains=term)
            | Q(events__description__icontains=term)
        )
        if request.user.has_perms(("payments.view_payment", "payments.view_financial_data")):
            query |= Q(payments__supplier__name__icontains=term)
            normalized = re.sub(r"\D", "", term)
            if len(normalized) in {11, 14}:
                query |= Q(payments__supplier__tax_id__icontains=normalized)
        return queryset.filter(query).distinct()
