from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.sectors.policies import evaluate_sector_access
from apps.audit.models import AuditAction
from apps.audit.services import record_audit

from .event_services import append_process_event
from .models import (
    AdministrativeProcess,
    ProcessMovement,
    ProcessMovementAction,
    ProcessStatus,
    ProcessEventType,
)


class ProcessDomainError(Exception):
    """Base error for workflow rules, intentionally independent from HTTP."""


class ProcessConflictError(ProcessDomainError):
    pass


class InvalidProcessTransition(ProcessDomainError):
    pass


class ProcessAccessDenied(ProcessDomainError):
    pass


class InvalidProcessDestination(ProcessDomainError):
    pass


TRANSITIONS = {
    ProcessMovementAction.OPEN: ({ProcessStatus.DRAFT}, ProcessStatus.OPEN),
    ProcessMovementAction.FORWARD: ({ProcessStatus.OPEN, ProcessStatus.IN_PROGRESS}, ProcessStatus.IN_PROGRESS),
    ProcessMovementAction.RECEIVE: ({ProcessStatus.IN_PROGRESS}, ProcessStatus.IN_PROGRESS),
    ProcessMovementAction.RETURN: ({ProcessStatus.IN_PROGRESS}, ProcessStatus.IN_PROGRESS),
    ProcessMovementAction.COMPLETE: ({ProcessStatus.OPEN, ProcessStatus.IN_PROGRESS}, ProcessStatus.COMPLETED),
    ProcessMovementAction.REOPEN: ({ProcessStatus.COMPLETED}, ProcessStatus.IN_PROGRESS),
    ProcessMovementAction.CANCEL: ({ProcessStatus.OPEN, ProcessStatus.IN_PROGRESS}, ProcessStatus.CANCELLED),
    ProcessMovementAction.ARCHIVE: ({ProcessStatus.COMPLETED, ProcessStatus.CANCELLED}, ProcessStatus.ARCHIVED),
}

PERMISSIONS = {
    ProcessMovementAction.OPEN: "processes.open_administrativeprocess",
    ProcessMovementAction.FORWARD: "processes.forward_administrativeprocess",
    ProcessMovementAction.RECEIVE: "processes.receive_administrativeprocess",
    ProcessMovementAction.RETURN: "processes.return_administrativeprocess",
    ProcessMovementAction.COMPLETE: "processes.complete_administrativeprocess",
    ProcessMovementAction.REOPEN: "processes.reopen_administrativeprocess",
    ProcessMovementAction.CANCEL: "processes.cancel_administrativeprocess",
    ProcessMovementAction.ARCHIVE: "processes.archive_administrativeprocess",
}


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
    append_process_event(
        process=process,
        event_type=ProcessEventType.PROCESS_CREATED,
        title="Processo criado",
        actor=user,
        payload={"status": process.status, "origin_sector_id": process.origin_sector_id},
    )
    return process


def _require_access(*, actor, action, process, sector):
    decision = evaluate_sector_access(
        actor,
        permission=PERMISSIONS[action],
        sector=sector,
        resource_state=process.status,
        allowed_states=TRANSITIONS[action][0],
        require_manager=action == ProcessMovementAction.REOPEN,
    )
    if not decision.allowed:
        raise ProcessAccessDenied(f"Ação não permitida: {decision.reason}.")


def _validate_version(process, expected_version):
    if expected_version is None or process.version != expected_version:
        raise ProcessConflictError(
            f"Versão desatualizada. Esperada {process.version}, recebida {expected_version}."
        )


def _validate_transition(process, action):
    allowed, _ = TRANSITIONS[action]
    if process.status not in allowed:
        raise InvalidProcessTransition(
            f"A ação {action} não é permitida no estado {process.status}."
        )


def _validate_destination(process, action, destination):
    if action not in {ProcessMovementAction.FORWARD, ProcessMovementAction.RETURN}:
        return process.current_sector
    if destination is None or not destination.active:
        raise InvalidProcessDestination("Selecione um setor de destino ativo.")
    if destination.pk == process.current_sector_id:
        raise InvalidProcessDestination("O setor de destino deve ser diferente do setor atual.")
    return destination


@transaction.atomic
def _perform_action(*, process_id, actor, action, expected_version, destination=None, note=""):
    process = (
        AdministrativeProcess.objects.select_for_update(of=("self",))
        .select_related("origin_sector", "current_sector")
        .get(pk=process_id)
    )
    _validate_version(process, expected_version)
    _validate_transition(process, action)

    source = process.current_sector
    access_sector = process.origin_sector if action == ProcessMovementAction.OPEN else source
    _require_access(actor=actor, action=action, process=process, sector=access_sector)

    if action in {ProcessMovementAction.RETURN, ProcessMovementAction.CANCEL, ProcessMovementAction.REOPEN} and not note.strip():
        raise InvalidProcessTransition("A observação é obrigatória para esta ação.")
    target = process.origin_sector if action == ProcessMovementAction.OPEN else _validate_destination(process, action, destination)
    if action == ProcessMovementAction.RECEIVE:
        last_action = process.movements.order_by("-created_at", "-id").values_list("action", flat=True).first()
        if last_action not in {ProcessMovementAction.FORWARD, ProcessMovementAction.RETURN}:
            raise InvalidProcessTransition("O processo só pode ser recebido após encaminhamento ou devolução.")

    status_before = process.status
    status_after = TRANSITIONS[action][1]
    now = timezone.now()
    process.status = status_after
    if action in {ProcessMovementAction.OPEN, ProcessMovementAction.FORWARD, ProcessMovementAction.RETURN}:
        process.current_sector = target
    if action == ProcessMovementAction.OPEN:
        process.opened_at = now
    elif action == ProcessMovementAction.COMPLETE:
        process.completed_at = now
    elif action == ProcessMovementAction.REOPEN:
        process.completed_at = None
        process.archived_at = None
    elif action == ProcessMovementAction.ARCHIVE:
        process.archived_at = now
    process.version += 1
    process.save()

    movement_source = None if action == ProcessMovementAction.OPEN else source
    movement_target = target if action in {ProcessMovementAction.OPEN, ProcessMovementAction.FORWARD, ProcessMovementAction.RETURN} else source
    ProcessMovement.objects.create(
        process=process,
        action=action,
        from_sector=movement_source,
        to_sector=movement_target,
        actor=actor,
        note=note.strip(),
        status_before=status_before,
        status_after=status_after,
    )
    record_audit(
        action=AuditAction.PROCESS_WORKFLOW,
        description=f"Ação de tramitação executada: {action}",
        user=actor,
        entity=process,
        old_values={"status": status_before, "sector_id": movement_source.pk if movement_source else None, "version": expected_version},
        new_values={"status": status_after, "sector_id": movement_target.pk if movement_target else None, "version": process.version, "action": action},
    )
    return process


def open_process(*, process_id, actor, expected_version, note=""):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.OPEN, expected_version=expected_version, note=note)


def forward_process(*, process_id, actor, destination, expected_version, note=""):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.FORWARD, destination=destination, expected_version=expected_version, note=note)


def receive_process(*, process_id, actor, expected_version, note=""):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.RECEIVE, expected_version=expected_version, note=note)


def return_process(*, process_id, actor, destination, expected_version, note):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.RETURN, destination=destination, expected_version=expected_version, note=note)


def complete_process(*, process_id, actor, expected_version, note=""):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.COMPLETE, expected_version=expected_version, note=note)


def reopen_process(*, process_id, actor, expected_version, note):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.REOPEN, expected_version=expected_version, note=note)


def cancel_process(*, process_id, actor, expected_version, note):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.CANCEL, expected_version=expected_version, note=note)


def archive_process(*, process_id, actor, expected_version, note=""):
    return _perform_action(process_id=process_id, actor=actor, action=ProcessMovementAction.ARCHIVE, expected_version=expected_version, note=note)
