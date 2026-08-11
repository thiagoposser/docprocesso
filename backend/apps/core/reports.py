from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, F, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError


def _integer(params, name):
    if not params.get(name):
        return None
    try:
        return int(params[name])
    except ValueError as error:
        raise ValidationError({name: "Informe um ID inteiro válido."}) from error


def _date(params, name):
    if not params.get(name):
        return None
    value = parse_date(params[name])
    if not value:
        raise ValidationError({name: "Use uma data no formato YYYY-MM-DD."})
    return value


def _decimal(params, name):
    if not params.get(name):
        return None
    try:
        return Decimal(params[name])
    except InvalidOperation as error:
        raise ValidationError({name: "Informe um valor decimal válido."}) from error


def process_report_queryset(user, params):
    from apps.processes.models import AdministrativeProcess, ProcessStatus

    queryset = AdministrativeProcess.objects.all()
    if not user.is_superuser:
        sectors = user.sector_memberships.filter(active=True, sector__active=True).values_list("sector_id", flat=True)
        queryset = queryset.filter(current_sector_id__in=sectors)
    filters = {
        "current_sector_id": _integer(params, "sector"),
        "process_type_id": _integer(params, "type"),
        "assigned_to_id": _integer(params, "responsible"),
    }
    queryset = queryset.filter(**{key: value for key, value in filters.items() if value is not None})
    if params.get("status"):
        if params["status"] not in ProcessStatus.values:
            raise ValidationError({"status": "Informe um status válido."})
        queryset = queryset.filter(status=params["status"])
    date_from, date_to = _date(params, "date_from"), _date(params, "date_to")
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    return queryset


def payment_report_queryset(user, params):
    from apps.payments.models import Payment, PaymentStatus

    queryset = Payment.objects.all()
    if not user.is_superuser:
        sectors = user.sector_memberships.filter(active=True, sector__active=True).values_list("sector_id", flat=True)
        queryset = queryset.filter(sector_id__in=sectors)
    filters = {"sector_id": _integer(params, "sector"), "supplier_id": _integer(params, "supplier")}
    queryset = queryset.filter(**{key: value for key, value in filters.items() if value is not None})
    if params.get("status"):
        if params["status"] not in PaymentStatus.values:
            raise ValidationError({"status": "Informe um status válido."})
        queryset = queryset.filter(status=params["status"])
    date_from, date_to = _date(params, "date_from"), _date(params, "date_to")
    if date_from:
        queryset = queryset.filter(due_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(due_date__lte=date_to)
    minimum, maximum = _decimal(params, "min_amount"), _decimal(params, "max_amount")
    if minimum is not None:
        queryset = queryset.filter(amount__gte=minimum)
    if maximum is not None:
        queryset = queryset.filter(amount__lte=maximum)
    if params.get("purpose"):
        queryset = queryset.filter(description__icontains=params["purpose"])
    return queryset


def process_summary(user, params):
    queryset = process_report_queryset(user, params)
    return {
        "total": queryset.count(),
        "by_status": list(queryset.values("status").annotate(count=Count("id")).order_by("status")),
        "by_type": list(queryset.values("process_type_id", name=F("process_type__name")).annotate(count=Count("id")).order_by("name")),
    }


def time_by_sector(user, params):
    from apps.processes.models import ProcessMovement

    process_ids = process_report_queryset(user, params).values_list("id", flat=True)
    movements = ProcessMovement.objects.filter(process_id__in=process_ids).select_related("to_sector").order_by("process_id", "created_at", "id")
    grouped, previous = defaultdict(list), {}
    now = timezone.now()
    for movement in movements:
        prior = previous.get(movement.process_id)
        if prior and prior.to_sector_id:
            grouped[(prior.to_sector_id, prior.to_sector.name)].append((movement.created_at - prior.created_at).total_seconds() / 3600)
        previous[movement.process_id] = movement
    for prior in previous.values():
        if prior.to_sector_id:
            grouped[(prior.to_sector_id, prior.to_sector.name)].append((now - prior.created_at).total_seconds() / 3600)
    return [{"sector": key[0], "sector_name": key[1], "average_hours": round(sum(values) / len(values), 2), "movements": len(values)} for key, values in sorted(grouped.items(), key=lambda item: item[0][1])]


def payment_summary(user, params):
    queryset = payment_report_queryset(user, params)
    totals = queryset.aggregate(count=Count("id"), total=Sum("amount"), average=Avg("amount"))
    return {"count": totals["count"], "total": str(totals["total"] or 0), "average": str(totals["average"] or 0), "by_status": list(queryset.values("status").annotate(count=Count("id"), total=Sum("amount")).order_by("status"))}


def payments_grouped(user, params, field, name, output_key):
    rows = payment_report_queryset(user, params).values(group_id=F(field), name=F(name)).annotate(count=Count("id"), total=Sum("amount")).order_by("name")
    return [{output_key: row.pop("group_id"), **row} for row in rows]
