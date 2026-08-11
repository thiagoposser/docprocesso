from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.sectors.policies import evaluate_sector_access

from .models import AdministrativeProcess


@transaction.atomic
def create_process(*, user, **validated_data):
    origin_sector = validated_data["origin_sector"]
    decision = evaluate_sector_access(
        user,
        permission="processes.add_administrativeprocess",
        sector=origin_sector,
    )
    if not decision.allowed:
        raise PermissionDenied("Você não pode criar processos neste setor.")
    process = AdministrativeProcess(created_by=user, **validated_data)
    process.save()
    return process
