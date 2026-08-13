from django.core.exceptions import ValidationError

from .models import AdministrativeWorkflow


def resolve_process_workflow(*, process_type, origin_sector):
    workflows = AdministrativeWorkflow.objects.filter(active=True, current_version__isnull=False).select_related(
        "current_version"
    )
    if process_type.workflow_id:
        workflows = workflows.filter(pk=process_type.workflow_id)
    candidates = list(workflows[:2])
    if not candidates:
        raise ValidationError({"process_type": "Nenhum fluxo ativo foi configurado para esta classificação."})
    if len(candidates) > 1:
        raise ValidationError({"process_type": "Associe a classificação a um fluxo para eliminar a ambiguidade."})
    workflow = candidates[0]
    initial_stages = list(workflow.current_version.stages.filter(is_initial=True)[:2])
    if len(initial_stages) != 1:
        raise ValidationError({"process_type": "O fluxo deve possuir exatamente uma etapa inicial."})
    initial = initial_stages[0]
    if initial.responsible_sector_id and initial.responsible_sector_id != origin_sector.id:
        raise ValidationError({"origin_sector": "O vínculo de origem não é elegível para a etapa inicial deste fluxo."})
    return workflow.current_version, initial
