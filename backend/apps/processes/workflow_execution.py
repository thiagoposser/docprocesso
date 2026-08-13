from django.db import transaction

from .models import AdministrativeProcess, WorkflowStage, WorkflowTransition
from .services import forward_process, return_process
from .workflow_policies import evaluate_transition_authorization


class TransitionDenied(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class TransitionVersionConflict(Exception):
    pass


class UnresolvedTransitionSector(Exception):
    pass


@transaction.atomic
def authorize_transition_execution(
    *, user, transition_id, current_stage_id, expected_workflow_version_id,
    process_status, permission, note="", has_attachment=False,
    responsible_sector_id=None, responsible_function_id=None,
    available_document_roles=(),
):
    current_stage = WorkflowStage.objects.select_for_update().select_related("workflow_version__workflow").get(
        pk=current_stage_id
    )
    transition = WorkflowTransition.objects.select_for_update(of=("self",)).select_related(
        "source_stage", "destination_stage", "authorized_sector", "authorized_function"
    ).get(pk=transition_id)
    if current_stage.workflow_version_id != expected_workflow_version_id:
        raise TransitionVersionConflict("A versão do fluxo foi alterada.")
    decision = evaluate_transition_authorization(
        user, transition=transition, current_stage=current_stage, process_status=process_status,
        permission=permission, note=note, has_attachment=has_attachment,
        responsible_sector_id=responsible_sector_id, responsible_function_id=responsible_function_id,
        available_document_roles=available_document_roles,
    )
    if not decision.allowed:
        raise TransitionDenied(decision.reason)
    return transition


@transaction.atomic
def execute_semantic_movement(
    *, user, process_id, transition_id, current_stage_id, expected_process_version,
    expected_workflow_version_id, note="", has_attachment=False,
    available_document_roles=(), permission_override=None,
):
    process = AdministrativeProcess.objects.select_for_update(of=("self",)).select_related("current_sector", "origin_sector").get(
        pk=process_id
    )
    process_sector_id = process.current_sector_id or process.origin_sector_id
    if process.current_stage_id != current_stage_id or process.responsible_sector_id != process_sector_id:
        raise TransitionDenied("stage_does_not_match_process_sector")
    permission = permission_override or (
        "processes.return_administrativeprocess"
        if WorkflowTransition.objects.only("is_return").get(pk=transition_id).is_return
        else "processes.forward_administrativeprocess"
    )
    transition = authorize_transition_execution(
        user=user, transition_id=transition_id, current_stage_id=current_stage_id,
        expected_workflow_version_id=expected_workflow_version_id, process_status=process.status,
        permission=permission, note=note, has_attachment=has_attachment,
        responsible_sector_id=process.responsible_sector_id,
        responsible_function_id=process.responsible_function_id,
        available_document_roles=available_document_roles,
    )
    destination = transition.destination_stage.responsible_sector
    if destination is None:
        raise UnresolvedTransitionSector("A etapa de destino não possui setor responsável.")
    service = return_process if transition.is_return else forward_process
    updated = service(
        process_id=process.pk, actor=user, destination=destination,
        expected_version=expected_process_version, note=note, workflow_transition=transition,
        access_permission=permission_override,
    )
    return updated
