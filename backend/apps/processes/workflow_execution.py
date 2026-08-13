from django.db import transaction

from .models import WorkflowStage, WorkflowTransition
from .workflow_policies import evaluate_transition_authorization


class TransitionDenied(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class TransitionVersionConflict(Exception):
    pass


@transaction.atomic
def authorize_transition_execution(
    *, user, transition_id, current_stage_id, expected_workflow_version_id,
    process_status, permission, note="", has_attachment=False,
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
    )
    if not decision.allowed:
        raise TransitionDenied(decision.reason)
    return transition
