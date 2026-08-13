from django.db import transaction

from .models import AdministrativeWorkflow, WorkflowStage, WorkflowVersion


@transaction.atomic
def create_workflow(*, code, name, description="", active=True):
    workflow = AdministrativeWorkflow.objects.create(code=code, active=active)
    version = WorkflowVersion.objects.create(workflow=workflow, version=1, name=name, description=description)
    workflow.current_version = version
    workflow.save(update_fields=["current_version", "updated_at"])
    return workflow


@transaction.atomic
def update_workflow(*, workflow, name=None, description=None, active=None):
    current = workflow.current_version
    next_name = current.name if name is None else name
    next_description = current.description if description is None else description
    if next_name != current.name or next_description != current.description:
        version = WorkflowVersion.objects.create(
            workflow=workflow, version=current.version + 1, name=next_name, description=next_description
        )
        WorkflowStage.objects.bulk_create([
            WorkflowStage(
                workflow_version=version, order=stage.order, name=stage.name, description=stage.description,
                is_initial=stage.is_initial, is_final=stage.is_final,
                responsible_sector=stage.responsible_sector,
                responsible_function=stage.responsible_function, requires_manager=stage.requires_manager,
            )
            for stage in current.stages.all()
        ])
        workflow.current_version = version
    if active is not None:
        workflow.active = active
    workflow.save()
    return workflow
