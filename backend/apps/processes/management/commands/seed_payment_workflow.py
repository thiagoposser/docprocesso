from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.sectors.models import OrganizationalFunction, Sector
from apps.processes.models import (
    AdministrativeWorkflow, ProcessType, WorkflowStage, WorkflowTransition,
)
from apps.processes.workflow_services import create_workflow


class Command(BaseCommand):
    help = "Cria idempotentemente o fluxo inicial de Pagamento Administrativo."

    def add_arguments(self, parser):
        parser.add_argument("--requester-sector-code", required=True)
        parser.add_argument("--management-sector-code", required=True)
        parser.add_argument("--finance-sector-code", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        sectors = {
            key: self._active_sector(options[argument])
            for key, argument in (
                ("requester", "requester_sector_code"),
                ("management", "management_sector_code"),
                ("finance", "finance_sector_code"),
            )
        }
        functions = {
            "assistant": self._function("ASSISTENTE", "Assistente"),
            "manager": self._function("GERENTE", "Gerente"),
            "finance": self._function("FINANCEIRO", "Financeiro"),
        }
        workflow = AdministrativeWorkflow.objects.select_related("current_version").filter(
            code="pagamento-administrativo"
        ).first()
        if workflow is None:
            workflow = create_workflow(
                code="pagamento-administrativo", name="Pagamento Administrativo",
                description="Criação, aprovação, processamento financeiro, pagamento, comprovante e finalização.",
            )
        elif workflow.current_version is None:
            raise CommandError("O fluxo existente não possui versão atual; nenhuma alteração foi feita.")

        version = workflow.current_version
        stage_specs = [
            (1, "Criação pelo solicitante", "requester", "assistant", True, False),
            (2, "Aprovação da Gerência", "management", "manager", False, False),
            (3, "Processamento Financeiro", "finance", "finance", False, False),
            (4, "Pagamento", "finance", "finance", False, False),
            (5, "Comprovante", "finance", "finance", False, False),
            (6, "Finalização", "management", "manager", False, True),
        ]
        stages = {}
        for order, name, sector_key, function_key, initial, final in stage_specs:
            expected = {
                "name": name, "description": "", "is_initial": initial, "is_final": final,
                "responsible_sector": sectors[sector_key], "responsible_function": functions[function_key],
                "requires_manager": function_key == "manager",
            }
            stage, created = WorkflowStage.objects.get_or_create(
                workflow_version=version, order=order, defaults=expected
            )
            if not created and any(getattr(stage, field) != value for field, value in expected.items()):
                raise CommandError(f"A etapa {order} existente diverge do seed; nenhuma configuração foi sobrescrita.")
            stages[order] = stage

        transition_specs = [
            (1, 2, "enviar-aprovacao", "Enviar para aprovação", "requester", "assistant", False, False),
            (2, 3, "aprovar", "Aprovar", "management", "manager", False, False),
            (2, 1, "devolver-solicitante", "Devolver ao solicitante", "management", "manager", True, False),
            (3, 4, "encaminhar-pagamento", "Encaminhar para pagamento", "finance", "finance", False, False),
            (3, 2, "devolver-gerencia", "Devolver à Gerência", "finance", "finance", True, False),
            (4, 5, "confirmar-pagamento", "Confirmar pagamento", "finance", "finance", False, False),
            (5, 6, "anexar-comprovante", "Anexar comprovante e finalizar", "finance", "finance", False, True),
            (5, 4, "devolver-pagamento", "Devolver ao pagamento", "finance", "finance", True, False),
            (6, 5, "reabrir-comprovante", "Reabrir comprovante", "management", "manager", True, False),
        ]
        for source, destination, code, name, sector_key, function_key, is_return, attachment in transition_specs:
            expected = {
                "name": name, "destination_stage": stages[destination],
                "authorized_sector": sectors[sector_key], "authorized_function": functions[function_key],
                "requires_note": is_return, "requires_attachment": attachment,
                "is_return": is_return, "active": True,
            }
            transition, created = WorkflowTransition.objects.get_or_create(
                source_stage=stages[source], code=code, defaults=expected
            )
            if not created and any(getattr(transition, field) != value for field, value in expected.items()):
                raise CommandError(f"A transição {code} existente diverge do seed; nenhuma configuração foi sobrescrita.")

        process_type, created = ProcessType.objects.get_or_create(
            code="pagamento-administrativo",
            defaults={"name": "Pagamento Administrativo", "description": "Processo administrativo de pagamento.", "workflow": workflow},
        )
        if not created and process_type.workflow_id not in (None, workflow.pk):
            raise CommandError("O tipo Pagamento Administrativo já está associado a outro fluxo.")
        if process_type.workflow_id is None:
            process_type.workflow = workflow
            process_type.save(update_fields=["workflow", "updated_at"])

        self._validate_graph(stages, version)
        self.stdout.write(self.style.SUCCESS("Fluxo Pagamento Administrativo configurado e validado."))

    def _active_sector(self, code):
        sector = Sector.objects.filter(code__iexact=code.strip(), active=True).first()
        if sector is None:
            raise CommandError(f"Setor ativo não encontrado para o código {code!r}.")
        return sector

    def _function(self, code, name):
        function, created = OrganizationalFunction.objects.get_or_create(code=code, defaults={"name": name})
        if not function.active or function.name != name:
            raise CommandError(f"A função {code} existente é inativa ou incompatível.")
        return function

    def _validate_graph(self, stages, version):
        initial = [stage for stage in stages.values() if stage.is_initial]
        final = [stage for stage in stages.values() if stage.is_final]
        if len(initial) != 1 or len(final) != 1:
            raise CommandError("O fluxo deve possuir exatamente uma etapa inicial e uma final.")
        reachable = {initial[0].pk}
        pending = [initial[0].pk]
        while pending:
            destinations = WorkflowTransition.objects.filter(
                source_stage_id=pending.pop(), active=True
            ).values_list("destination_stage_id", flat=True)
            for destination in destinations:
                if destination not in reachable:
                    reachable.add(destination)
                    pending.append(destination)
        expected = set(WorkflowStage.objects.filter(workflow_version=version).values_list("pk", flat=True))
        if reachable != expected or final[0].pk not in reachable:
            raise CommandError("O grafo contém etapas inalcançáveis.")
