from dataclasses import dataclass

from apps.sectors.models import UserSectorMembership

from .models import ProcessStatus, WorkflowStage, WorkflowTransition


TERMINAL_PROCESS_STATES = {ProcessStatus.COMPLETED, ProcessStatus.CANCELLED, ProcessStatus.ARCHIVED}


@dataclass(frozen=True)
class TransitionAuthorizationDecision:
    allowed: bool
    reason: str


def evaluate_transition_authorization(
    user, *, transition, current_stage, process_status, permission, note="", has_attachment=False,
    responsible_sector_id=None, responsible_function_id=None,
):
    if not getattr(user, "is_authenticated", False):
        return TransitionAuthorizationDecision(False, "authentication_required")
    if not isinstance(transition, WorkflowTransition) or not transition.active:
        return TransitionAuthorizationDecision(False, "inactive_or_invalid_transition")
    if not isinstance(current_stage, WorkflowStage) or transition.source_stage_id != current_stage.id:
        return TransitionAuthorizationDecision(False, "transition_not_available_from_current_stage")
    if process_status in TERMINAL_PROCESS_STATES:
        return TransitionAuthorizationDecision(False, "terminal_process")
    if not user.has_perm(permission):
        return TransitionAuthorizationDecision(False, "permission_required")
    if transition.requires_note and not note.strip():
        return TransitionAuthorizationDecision(False, "note_required")
    if transition.requires_attachment and not has_attachment:
        return TransitionAuthorizationDecision(False, "attachment_required")
    if user.is_superuser:
        return TransitionAuthorizationDecision(True, "superuser")

    memberships = UserSectorMembership.objects.effective().filter(user=user)
    if transition.authorized_sector_id:
        memberships = memberships.filter(sector_id=transition.authorized_sector_id)
    if transition.authorized_function_id:
        memberships = memberships.filter(function_id=transition.authorized_function_id)
    if not transition.authorized_sector_id and not transition.authorized_function_id:
        source = responsible_sector_id or current_stage.responsible_sector_id
        function = responsible_function_id if responsible_function_id is not None else current_stage.responsible_function_id
        if source:
            memberships = memberships.filter(sector_id=source)
        if function:
            memberships = memberships.filter(function_id=function)
    if not memberships.exists():
        return TransitionAuthorizationDecision(False, "eligible_membership_required")
    return TransitionAuthorizationDecision(True, "allowed")


def available_transitions(user, *, current_stage, process_status, permission):
    transitions = current_stage.outgoing_transitions.filter(active=True).select_related(
        "source_stage", "destination_stage", "authorized_sector", "authorized_function"
    )
    return [
        transition for transition in transitions
        if evaluate_transition_authorization(
            user, transition=transition, current_stage=current_stage, process_status=process_status,
            permission=permission, note="requirement-preview" if transition.requires_note else "",
            has_attachment=transition.requires_attachment,
        ).allowed
    ]
