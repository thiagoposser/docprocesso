from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditAction, AuditLog
from apps.sectors.models import Sector, UserSectorMembership

from .event_services import append_process_event
from .models import AdministrativeProcess, ProcessEvent, ProcessEventType, ProcessMovement, ProcessMovementAction, ProcessStatus, ProcessType
from .services import (
    InvalidProcessDestination,
    InvalidProcessTransition,
    ProcessAccessDenied,
    ProcessConflictError,
    archive_process,
    cancel_process,
    complete_process,
    forward_process,
    open_process,
    receive_process,
    reopen_process,
    return_process,
)


class AdministrativeProcessModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="process_author")
        self.sector = Sector.objects.create(name="Protocolo", code="PROTO")
        self.process_type = ProcessType.objects.create(name="Administrativo", code="administrativo")

    def make_process(self, **changes):
        values = {
            "title": "Aquisição de material",
            "process_type": self.process_type,
            "created_by": self.user,
            "origin_sector": self.sector,
        }
        values.update(changes)
        return AdministrativeProcess.objects.create(**values)

    def test_creates_consistent_draft_with_unique_opaque_number(self):
        first = self.make_process()
        second = self.make_process(title="Segundo processo")

        self.assertEqual(first.status, ProcessStatus.DRAFT)
        self.assertEqual(first.version, 1)
        self.assertIsNone(first.current_sector)
        self.assertTrue(first.number.startswith("DP-"))
        self.assertNotEqual(first.number, second.number)

    def test_requires_current_sector_outside_draft(self):
        with self.assertRaisesMessage(ValidationError, "setor atual é obrigatório"):
            self.make_process(status=ProcessStatus.OPEN, opened_at=timezone.now())

    def test_requires_dates_for_terminal_states(self):
        with self.assertRaisesMessage(ValidationError, "data de conclusão é obrigatória"):
            self.make_process(status=ProcessStatus.COMPLETED, current_sector=self.sector)
        with self.assertRaisesMessage(ValidationError, "data de arquivamento é obrigatória"):
            self.make_process(status=ProcessStatus.ARCHIVED, current_sector=self.sector)

    def test_generic_save_does_not_apply_lifecycle_side_effects(self):
        process = self.make_process(current_sector=self.sector)
        process.status = ProcessStatus.OPEN
        process.save()

        self.assertIsNone(process.opened_at)
        self.assertEqual(process.version, 1)

    def test_rejects_invalid_version(self):
        with self.assertRaisesMessage(ValidationError, "versão deve ser maior"):
            self.make_process(version=0)

    def test_referenced_records_are_protected(self):
        self.make_process(current_sector=self.sector, assignee=self.user)

        for referenced in (self.process_type, self.sector, self.user):
            with self.assertRaises(ProtectedError):
                referenced.delete()

    def test_declares_action_permissions_and_no_delete_permission(self):
        self.assertEqual(AdministrativeProcess._meta.default_permissions, ("add", "change", "view"))
        codenames = {codename for codename, _ in AdministrativeProcess._meta.permissions}
        self.assertEqual(
            codenames,
            {
                "open_administrativeprocess",
                "forward_administrativeprocess",
                "receive_administrativeprocess",
                "return_administrativeprocess",
                "complete_administrativeprocess",
                "reopen_administrativeprocess",
                "cancel_administrativeprocess",
                "archive_administrativeprocess",
            },
        )


class AdministrativeProcessApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="process_api_user")
        self.other = users.objects.create_user(username="process_api_other")
        self.sector = Sector.objects.create(name="API Protocolo", code="API-PROTO")
        self.other_sector = Sector.objects.create(name="API Restrito", code="API-REST")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        UserSectorMembership.objects.create(user=self.other, sector=self.other_sector, is_primary=True)
        self.process_type = ProcessType.objects.create(name="API Administrativo", code="api-administrativo")
        permissions = Permission.objects.filter(
            codename__in=["view_administrativeprocess", "add_administrativeprocess", "change_administrativeprocess"]
        )
        self.user.user_permissions.add(*permissions)
        self.other.user_permissions.add(*permissions)
        self.client.force_authenticate(self.user)

    def create_process(self, *, user=None, sector=None, **changes):
        values = {
            "title": "Processo visível",
            "process_type": self.process_type,
            "created_by": user or self.user,
            "origin_sector": sector or self.sector,
        }
        values.update(changes)
        return AdministrativeProcess.objects.create(**values)

    def test_creates_lists_retrieves_and_edits_draft(self):
        created = self.client.post(
            reverse("process-list"),
            {"title": "Compra", "description": "Material", "process_type": self.process_type.pk, "origin_sector": self.sector.pk},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["created_by"], self.user.pk)
        listed = self.client.get(reverse("process-list"))
        self.assertEqual(listed.data["count"], 1)
        detail = reverse("process-detail", args=[created.data["id"]])
        updated = self.client.patch(detail, {"title": "Compra atualizada"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["title"], "Compra atualizada")
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_isolates_queryset_and_returns_404_outside_sector_scope(self):
        visible = self.create_process()
        hidden = self.create_process(user=self.other, sector=self.other_sector, title="Sigiloso")

        response = self.client.get(reverse("process-list"), {"search": "Sigiloso"})
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(self.client.get(reverse("process-detail", args=[hidden.pk])).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse("process-detail", args=[visible.pk])).status_code, status.HTTP_200_OK)

    def test_rejects_creation_outside_scope_and_protected_patch_fields(self):
        denied = self.client.post(
            reverse("process-list"),
            {"title": "Negado", "process_type": self.process_type.pk, "origin_sector": self.other_sector.pk},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        process = self.create_process()
        response = self.client.patch(
            reverse("process-detail", args=[process.pk]),
            {"status": ProcessStatus.OPEN, "current_sector": self.other_sector.pk, "version": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)
        relocation = self.client.patch(
            reverse("process-detail", args=[process.pk]),
            {"origin_sector": self.other_sector.pk},
            format="json",
        )
        self.assertEqual(relocation.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("origin_sector", relocation.data)

    def test_requires_permissions_and_membership_for_reading(self):
        unprivileged = get_user_model().objects.create_user(username="process_unprivileged")
        UserSectorMembership.objects.create(user=unprivileged, sector=self.sector)
        self.client.force_authenticate(unprivileged)
        self.assertEqual(self.client.get(reverse("process-list")).status_code, status.HTTP_403_FORBIDDEN)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("process-list")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filters_only_within_scope_and_validates_parameters(self):
        first = self.create_process(title="Contrato alfa", assignee=self.user)
        self.create_process(title="Outro", status=ProcessStatus.OPEN, current_sector=self.sector)

        response = self.client.get(
            reverse("process-list"),
            {"number": first.number[3:10], "type": self.process_type.pk, "status": ProcessStatus.DRAFT, "sector": self.sector.pk, "assignee": self.user.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.client.get(reverse("process-list"), {"created_from": "invalid"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(reverse("process-list"), {"status": "UNKNOWN"}).status_code, status.HTTP_400_BAD_REQUEST)

    def test_lists_only_active_process_types(self):
        ProcessType.objects.create(name="Inativo", code="inativo", active=False)
        response = self.client.get(reverse("process-type-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [self.process_type.pk])


class ProcessMovementModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="movement_actor")
        self.origin = Sector.objects.create(name="Movimento origem", code="MOV-O")
        self.destination = Sector.objects.create(name="Movimento destino", code="MOV-D")
        process_type = ProcessType.objects.create(name="Movimentação", code="movimentacao")
        self.process = AdministrativeProcess.objects.create(
            title="Processo movimentado",
            process_type=process_type,
            created_by=self.user,
            origin_sector=self.origin,
        )

    def movement(self, **changes):
        values = {
            "process": self.process,
            "action": ProcessMovementAction.OPEN,
            "from_sector": None,
            "to_sector": self.origin,
            "actor": self.user,
            "status_before": ProcessStatus.DRAFT,
            "status_after": ProcessStatus.OPEN,
        }
        values.update(changes)
        return ProcessMovement.objects.create(**values)

    def test_records_ordered_append_only_history(self):
        first = self.movement()
        second = self.movement(
            action=ProcessMovementAction.FORWARD,
            from_sector=self.origin,
            to_sector=self.destination,
            status_before=ProcessStatus.OPEN,
            status_after=ProcessStatus.IN_PROGRESS,
        )

        self.assertEqual(list(ProcessMovement.objects.for_process(self.process)), [first, second])
        self.assertEqual(ProcessMovement._meta.default_permissions, ("view",))

    def test_rejects_instance_and_queryset_mutation(self):
        movement = self.movement()
        movement.note = "alterado"
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            movement.save()
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            ProcessMovement.objects.filter(pk=movement.pk).update(note="alterado")
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            movement.delete()
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            ProcessMovement.objects.filter(pk=movement.pk).delete()

    def test_requires_note_for_return_cancel_and_reopen(self):
        for action in (ProcessMovementAction.RETURN, ProcessMovementAction.CANCEL, ProcessMovementAction.REOPEN):
            values = {"action": action, "from_sector": self.origin, "to_sector": self.destination}
            if action in {ProcessMovementAction.CANCEL, ProcessMovementAction.REOPEN}:
                values["to_sector"] = self.origin
            with self.assertRaisesMessage(ValidationError, "observação é obrigatória"):
                self.movement(**values)

    def test_enforces_sector_coherence_by_action(self):
        with self.assertRaisesMessage(ValidationError, "somente o setor de destino"):
            self.movement(from_sector=self.origin)
        with self.assertRaisesMessage(ValidationError, "origem e destino diferentes"):
            self.movement(action=ProcessMovementAction.FORWARD, from_sector=self.origin, to_sector=self.origin)
        with self.assertRaisesMessage(ValidationError, "permanecer no mesmo setor"):
            self.movement(action=ProcessMovementAction.RECEIVE, from_sector=self.origin, to_sector=self.destination)
        with self.assertRaisesMessage(ValidationError, "ação de estado"):
            self.movement(action=ProcessMovementAction.COMPLETE, from_sector=None, to_sector=None)

    def test_referenced_records_are_protected(self):
        self.movement()
        for referenced in (self.process, self.origin, self.user):
            with self.assertRaises(ProtectedError):
                referenced.delete()

    def test_declares_expected_indexes(self):
        names = {index.name for index in ProcessMovement._meta.indexes}
        self.assertEqual(names, {"movement_process_date_idx", "movement_from_date_idx", "movement_to_date_idx", "movement_action_date_idx"})


class ProcessWorkflowServiceTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.actor = users.objects.create_user(username="workflow_actor")
        self.outsider = users.objects.create_user(username="workflow_outsider")
        self.origin = Sector.objects.create(name="Fluxo origem", code="FLOW-O")
        self.destination = Sector.objects.create(name="Fluxo destino", code="FLOW-D")
        UserSectorMembership.objects.create(user=self.actor, sector=self.origin, active=True, is_primary=True, is_manager=True)
        UserSectorMembership.objects.create(user=self.actor, sector=self.destination, active=True, is_manager=True)
        process_type = ProcessType.objects.create(name="Fluxo", code="fluxo")
        self.process = AdministrativeProcess.objects.create(
            title="Fluxo completo",
            process_type=process_type,
            created_by=self.actor,
            origin_sector=self.origin,
        )
        codenames = [
            "open_administrativeprocess", "forward_administrativeprocess", "receive_administrativeprocess",
            "return_administrativeprocess", "complete_administrativeprocess", "reopen_administrativeprocess",
            "cancel_administrativeprocess", "archive_administrativeprocess",
        ]
        permissions = Permission.objects.filter(codename__in=codenames)
        self.actor.user_permissions.add(*permissions)
        self.outsider.user_permissions.add(*permissions)

    def test_complete_workflow_updates_state_version_dates_and_movements_atomically(self):
        process = open_process(process_id=self.process.pk, actor=self.actor, expected_version=1)
        self.assertEqual((process.status, process.current_sector, process.version), (ProcessStatus.OPEN, self.origin, 2))
        self.assertIsNotNone(process.opened_at)
        process = forward_process(process_id=process.pk, actor=self.actor, destination=self.destination, expected_version=2)
        process = receive_process(process_id=process.pk, actor=self.actor, expected_version=3)
        process = complete_process(process_id=process.pk, actor=self.actor, expected_version=4)
        self.assertEqual(process.status, ProcessStatus.COMPLETED)
        self.assertIsNotNone(process.completed_at)
        process = reopen_process(process_id=process.pk, actor=self.actor, expected_version=5, note="Necessário complementar")
        self.assertEqual(process.status, ProcessStatus.IN_PROGRESS)
        self.assertIsNone(process.completed_at)
        process = return_process(process_id=process.pk, actor=self.actor, destination=self.origin, expected_version=6, note="Corrigir dados")
        process = receive_process(process_id=process.pk, actor=self.actor, expected_version=7)
        process = cancel_process(process_id=process.pk, actor=self.actor, expected_version=8, note="Demanda cancelada")
        process = archive_process(process_id=process.pk, actor=self.actor, expected_version=9)

        self.assertEqual((process.status, process.version), (ProcessStatus.ARCHIVED, 10))
        self.assertIsNotNone(process.archived_at)
        self.assertEqual(
            list(process.movements.values_list("action", flat=True)),
            ["OPEN", "FORWARD", "RECEIVE", "COMPLETE", "REOPEN", "RETURN", "RECEIVE", "CANCEL", "ARCHIVE"],
        )

    def test_rejects_stale_version_and_duplicate_action(self):
        process = open_process(process_id=self.process.pk, actor=self.actor, expected_version=1)
        with self.assertRaises(ProcessConflictError):
            forward_process(process_id=process.pk, actor=self.actor, destination=self.destination, expected_version=1)
        with self.assertRaises(InvalidProcessTransition):
            open_process(process_id=process.pk, actor=self.actor, expected_version=2)
        self.assertEqual(ProcessMovement.objects.count(), 1)

    def test_rejects_access_outside_sector_and_invalid_destination(self):
        with self.assertRaises(ProcessAccessDenied):
            open_process(process_id=self.process.pk, actor=self.outsider, expected_version=1)
        open_process(process_id=self.process.pk, actor=self.actor, expected_version=1)
        with self.assertRaises(InvalidProcessDestination):
            forward_process(process_id=self.process.pk, actor=self.actor, destination=self.origin, expected_version=2)
        self.destination.active = False
        self.destination.save()
        with self.assertRaises(InvalidProcessDestination):
            forward_process(process_id=self.process.pk, actor=self.actor, destination=self.destination, expected_version=2)

    def test_receive_requires_a_pending_transfer(self):
        open_process(process_id=self.process.pk, actor=self.actor, expected_version=1)
        with self.assertRaises(InvalidProcessTransition):
            receive_process(process_id=self.process.pk, actor=self.actor, expected_version=2)

    def test_movement_failure_rolls_back_process_change(self):
        from unittest.mock import patch

        with patch("apps.processes.services.ProcessMovement.objects.create", side_effect=RuntimeError("movement failure")):
            with self.assertRaises(RuntimeError):
                open_process(process_id=self.process.pk, actor=self.actor, expected_version=1)

        self.process.refresh_from_db()
        self.assertEqual((self.process.status, self.process.current_sector, self.process.version), (ProcessStatus.DRAFT, None, 1))
        self.assertFalse(ProcessMovement.objects.exists())

    def test_action_acquires_row_lock(self):
        with CaptureQueriesContext(connection) as queries:
            open_process(process_id=self.process.pk, actor=self.actor, expected_version=1)

        self.assertTrue(any("FOR UPDATE" in query["sql"].upper() for query in queries.captured_queries))


class ProcessWorkflowApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.actor = users.objects.create_user(username="workflow_api_actor")
        self.outsider = users.objects.create_user(username="workflow_api_outsider")
        self.origin = Sector.objects.create(name="API fluxo origem", code="API-FLOW-O")
        self.destination = Sector.objects.create(name="API fluxo destino", code="API-FLOW-D")
        self.other_sector = Sector.objects.create(name="API fluxo restrito", code="API-FLOW-X")
        UserSectorMembership.objects.create(user=self.actor, sector=self.origin, is_primary=True, is_manager=True)
        UserSectorMembership.objects.create(user=self.actor, sector=self.destination, is_manager=True)
        UserSectorMembership.objects.create(user=self.outsider, sector=self.other_sector, is_primary=True, is_manager=True)
        process_type = ProcessType.objects.create(name="API Fluxo", code="api-fluxo")
        self.process = AdministrativeProcess.objects.create(
            title="Fluxo via API", process_type=process_type, created_by=self.actor, origin_sector=self.origin,
        )
        codenames = [
            "view_administrativeprocess", "open_administrativeprocess", "forward_administrativeprocess",
            "receive_administrativeprocess", "return_administrativeprocess", "complete_administrativeprocess",
            "reopen_administrativeprocess", "cancel_administrativeprocess", "archive_administrativeprocess",
        ]
        permissions = Permission.objects.filter(codename__in=codenames)
        self.actor.user_permissions.add(*permissions)
        self.outsider.user_permissions.add(*permissions)
        self.client.force_authenticate(self.actor)

    def post_action(self, name, version, **payload):
        return self.client.post(reverse(f"process-{name}", args=[self.process.pk]), {"version": version, **payload}, format="json")

    def test_exposes_every_action_and_paginated_serialized_timeline(self):
        responses = [
            self.post_action("open", 1),
            self.post_action("forward", 2, destination=self.destination.pk, note="Encaminhar"),
            self.post_action("receive", 3),
            self.post_action("complete", 4),
            self.post_action("reopen", 5, note="Complementar"),
            self.post_action("return", 6, destination=self.origin.pk, note="Corrigir"),
            self.post_action("receive", 7),
            self.post_action("cancel", 8, note="Cancelado"),
            self.post_action("archive", 9),
        ]
        self.assertTrue(all(response.status_code == status.HTTP_200_OK for response in responses))
        self.assertEqual(responses[-1].data["status"], ProcessStatus.ARCHIVED)
        self.assertEqual(responses[-1].data["version"], 10)

        timeline = self.client.get(reverse("process-timeline", args=[self.process.pk]))
        self.assertEqual(timeline.status_code, status.HTTP_200_OK)
        self.assertEqual(timeline.data["count"], 9)
        self.assertEqual(timeline.data["results"][0]["action"], ProcessMovementAction.OPEN)
        self.assertEqual(timeline.data["results"][0]["actor_name"], self.actor.full_name)
        self.assertEqual(timeline.data["results"][1]["from_sector_name"], self.origin.name)
        self.assertEqual(timeline.data["results"][1]["to_sector_name"], self.destination.name)

    def test_maps_validation_permission_not_found_and_conflict_statuses(self):
        self.assertEqual(self.post_action("open", 0).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.post_action("open", 1).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.post_action("forward", 1, destination=self.destination.pk).status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            self.post_action("return", 2, destination=self.destination.pk, note="").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.client.force_authenticate(self.outsider)
        self.assertEqual(
            self.client.post(reverse("process-forward", args=[self.process.pk]), {"version": 2, "destination": self.other_sector.pk}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )

        no_permission = get_user_model().objects.create_user(username="workflow_api_no_permission")
        UserSectorMembership.objects.create(user=no_permission, sector=self.origin)
        self.client.force_authenticate(no_permission)
        self.assertEqual(
            self.client.post(reverse("process-forward", args=[self.process.pk]), {"version": 2, "destination": self.destination.pk}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_does_not_expose_generic_movement_write_endpoint(self):
        response = self.client.post("/api/process-movements/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_combines_functional_events_and_movements_once_in_timeline(self):
        append_process_event(
            process=self.process,
            event_type=ProcessEventType.NOTE,
            title="Informação complementar",
            actor=self.actor,
            description="Evento fora da tramitação",
        )
        self.assertEqual(self.post_action("open", 1).status_code, status.HTTP_200_OK)

        timeline = self.client.get(reverse("process-timeline", args=[self.process.pk]))

        self.assertEqual(timeline.data["count"], 2)
        self.assertEqual([item["kind"] for item in timeline.data["results"]], ["event", "movement"])
        self.assertEqual(timeline.data["results"][0]["event_type"], ProcessEventType.NOTE)
        self.assertEqual(timeline.data["results"][1]["action"], ProcessMovementAction.OPEN)


class ProcessEventTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user(username="event_actor")
        sector = Sector.objects.create(name="Eventos", code="EVENT")
        process_type = ProcessType.objects.create(name="Eventos", code="eventos")
        self.process = AdministrativeProcess.objects.create(
            title="Processo com eventos", process_type=process_type, created_by=self.actor, origin_sector=sector,
        )

    def test_service_sanitizes_limits_and_audits_event(self):
        event = append_process_event(
            process=self.process,
            event_type=ProcessEventType.DOCUMENT_CHANGED,
            title="Documento incluído",
            actor=self.actor,
            payload={
                "document_id": 10,
                "password": "never",
                "file_content": "binary",
                "bank_account": "secret",
                "description": "x" * 800,
                "nested": {"token": "never", "safe": True},
            },
        )

        self.assertEqual(event.payload["document_id"], 10)
        self.assertEqual(len(event.payload["description"]), 500)
        self.assertEqual(event.payload["nested"], {"safe": True})
        self.assertNotIn("password", event.payload)
        self.assertNotIn("file_content", event.payload)
        self.assertNotIn("bank_account", event.payload)
        audit = AuditLog.objects.get(action=AuditAction.PROCESS_EVENT)
        self.assertEqual(audit.entity_id, str(self.process.pk))
        self.assertEqual(audit.new_values["event_id"], event.pk)

    def test_events_are_append_only_and_corrections_preserve_original(self):
        original = append_process_event(
            process=self.process, event_type=ProcessEventType.NOTE, title="Informação original", actor=self.actor,
        )
        correction = append_process_event(
            process=self.process,
            event_type=ProcessEventType.CORRECTION,
            title="Correção",
            actor=self.actor,
            corrects_event=original,
            payload={"corrected_field": "title"},
        )

        self.assertEqual(ProcessEvent.objects.count(), 2)
        self.assertEqual(correction.payload["corrects_event_id"], original.pk)
        original.title = "Mutado"
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            original.save()
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            ProcessEvent.objects.filter(pk=original.pk).update(title="Mutado")
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            original.delete()

    def test_rejects_oversized_payload_and_cross_process_correction(self):
        oversized = {f"safe_{index}": "x" * 500 for index in range(50)}
        with self.assertRaisesMessage(ValidationError, "8 KB"):
            append_process_event(
                process=self.process, event_type=ProcessEventType.SYSTEM, title="Grande", payload=oversized,
            )

        other = AdministrativeProcess.objects.create(
            title="Outro processo", process_type=self.process.process_type,
            created_by=self.actor, origin_sector=self.process.origin_sector,
        )
        original = append_process_event(
            process=other, event_type=ProcessEventType.NOTE, title="Outro evento", actor=self.actor,
        )
        with self.assertRaisesMessage(ValidationError, "mesmo processo"):
            append_process_event(
                process=self.process, event_type=ProcessEventType.CORRECTION,
                title="Correção inválida", actor=self.actor, corrects_event=original,
            )

    def test_workflow_creates_audit_but_not_duplicate_functional_event(self):
        permission = Permission.objects.get(codename="open_administrativeprocess")
        self.actor.user_permissions.add(permission)
        UserSectorMembership.objects.create(user=self.actor, sector=self.process.origin_sector, is_primary=True)

        open_process(process_id=self.process.pk, actor=self.actor, expected_version=1)

        self.assertEqual(ProcessMovement.objects.count(), 1)
        self.assertEqual(ProcessEvent.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(action=AuditAction.PROCESS_WORKFLOW).count(), 1)
