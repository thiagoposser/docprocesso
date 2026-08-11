from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.documents.serializers import ProcessDocumentSerializer
from apps.documents.services import create_process_document

from .models import AdministrativeProcess, ProcessStatus, ProcessType
from .permissions import ProcessPermission, ProcessTypePermission
from .serializers import (
    ProcessActionSerializer,
    ProcessDestinationActionSerializer,
    ProcessDetailSerializer,
    ProcessListSerializer,
    ProcessTimelineEntrySerializer,
    ProcessRequiredNoteActionSerializer,
    ProcessReturnActionSerializer,
    ProcessTypeSerializer,
    ProcessWriteSerializer,
)
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


class ProcessViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [ProcessPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["number", "title", "description", "process_type__name"]
    ordering_fields = ["number", "title", "status", "opened_at", "completed_at", "created_at", "updated_at"]
    ordering = ["-updated_at", "id"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProcessListSerializer
        if self.action in {"create", "partial_update", "update"}:
            return ProcessWriteSerializer
        if self.action in {"forward"}:
            return ProcessDestinationActionSerializer
        if self.action in {"return_action"}:
            return ProcessReturnActionSerializer
        if self.action in {"reopen", "cancel"}:
            return ProcessRequiredNoteActionSerializer
        if self.action in {"open", "receive", "complete", "archive"}:
            return ProcessActionSerializer
        if self.action == "timeline":
            return ProcessTimelineEntrySerializer
        if self.action == "documents":
            return ProcessDocumentSerializer
        return ProcessDetailSerializer

    def get_queryset(self):
        queryset = AdministrativeProcess.objects.select_related(
            "process_type", "created_by", "origin_sector", "current_sector", "assignee"
        )
        user = self.request.user
        if not user.is_superuser:
            sector_ids = user.sector_memberships.filter(active=True, sector__active=True).values_list("sector_id", flat=True)
            queryset = queryset.filter(
                Q(current_sector_id__in=sector_ids)
                | Q(current_sector__isnull=True, origin_sector_id__in=sector_ids)
            )

        params = self.request.query_params
        integer_filters = {"type": "process_type_id", "assignee": "assignee_id"}
        for parameter, field in integer_filters.items():
            if params.get(parameter):
                try:
                    queryset = queryset.filter(**{field: int(params[parameter])})
                except ValueError as error:
                    raise ValidationError({parameter: "Informe um ID inteiro válido."}) from error
        if params.get("sector"):
            try:
                sector_id = int(params["sector"])
            except ValueError as error:
                raise ValidationError({"sector": "Informe um ID inteiro válido."}) from error
            queryset = queryset.filter(
                Q(current_sector_id=sector_id)
                | Q(current_sector__isnull=True, origin_sector_id=sector_id)
            )
        if params.get("number"):
            queryset = queryset.filter(number__icontains=params["number"])
        if params.get("status"):
            if params["status"] not in ProcessStatus.values:
                raise ValidationError({"status": "Informe um estado de processo válido."})
            queryset = queryset.filter(status=params["status"])
        for parameter, lookup in {
            "created_from": "created_at__date__gte",
            "created_to": "created_at__date__lte",
            "opened_from": "opened_at__date__gte",
            "opened_to": "opened_at__date__lte",
        }.items():
            if params.get(parameter):
                value = parse_date(params[parameter])
                if value is None:
                    raise ValidationError({parameter: "Use uma data no formato YYYY-MM-DD."})
                queryset = queryset.filter(**{lookup: value})
        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(ProcessDetailSerializer(instance, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(ProcessDetailSerializer(instance, context=self.get_serializer_context()).data)

    def _execute_action(self, request, service, *, destination=False):
        process = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arguments = {
            "process_id": process.pk,
            "actor": request.user,
            "expected_version": serializer.validated_data["version"],
            "note": serializer.validated_data.get("note", ""),
        }
        if destination:
            arguments["destination"] = serializer.validated_data["destination"]
        try:
            updated = service(**arguments)
        except ProcessConflictError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except ProcessAccessDenied as error:
            raise PermissionDenied(str(error)) from error
        except (InvalidProcessTransition, InvalidProcessDestination) as error:
            raise ValidationError({"detail": str(error)}) from error
        except AdministrativeProcess.DoesNotExist as error:
            raise NotFound("Processo não encontrado.") from error
        return Response(ProcessDetailSerializer(updated, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        return self._execute_action(request, open_process)

    @action(detail=True, methods=["post"])
    def forward(self, request, pk=None):
        return self._execute_action(request, forward_process, destination=True)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        return self._execute_action(request, receive_process)

    @action(detail=True, methods=["post"], url_path="return", url_name="return")
    def return_action(self, request, pk=None):
        return self._execute_action(request, return_process, destination=True)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._execute_action(request, complete_process)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._execute_action(request, reopen_process)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._execute_action(request, cancel_process)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._execute_action(request, archive_process)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        process = self.get_object()
        movements = process.movements.select_related("actor", "from_sector", "to_sector").chronological()
        events = process.events.select_related("actor").chronological()
        entries = [
            {
                "kind": "movement", "id": f"movement-{item.pk}", "action": item.action,
                "action_label": item.get_action_display(), "event_type": None, "event_type_label": None,
                "title": item.get_action_display(), "actor": item.actor_id, "actor_name": item.actor.full_name,
                "from_sector": item.from_sector_id, "from_sector_name": item.from_sector.name if item.from_sector else None,
                "to_sector": item.to_sector_id, "to_sector_name": item.to_sector.name if item.to_sector else None,
                "note": item.note, "payload": {}, "status_before": item.status_before,
                "status_before_label": item.get_status_before_display(), "status_after": item.status_after,
                "status_after_label": item.get_status_after_display(), "created_at": item.created_at,
            }
            for item in movements
        ] + [
            {
                "kind": "event", "id": f"event-{item.pk}", "action": None, "action_label": None,
                "event_type": item.event_type, "event_type_label": item.get_event_type_display(),
                "title": item.title, "actor": item.actor_id, "actor_name": item.actor.full_name if item.actor else None,
                "from_sector": None, "from_sector_name": None, "to_sector": None, "to_sector_name": None,
                "note": item.description, "payload": item.payload, "status_before": None,
                "status_before_label": None, "status_after": None, "status_after_label": None,
                "created_at": item.created_at,
            }
            for item in events
        ]
        entries.sort(key=lambda item: (item["created_at"], item["id"]))
        page = self.paginate_queryset(entries)
        serializer = ProcessTimelineEntrySerializer(page if page is not None else entries, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=True, methods=["get", "post"])
    def documents(self, request, pk=None):
        process = self.get_object()
        if request.method == "GET":
            if not request.user.has_perm("documents.view_document"):
                self.permission_denied(request)
            queryset = process.documents.select_related("category", "created_by").prefetch_related("attachments")
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page if page is not None else queryset, many=True)
            return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
        if not request.user.has_perm("documents.add_document"):
            self.permission_denied(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = create_process_document(
            process=process, actor=request.user, request=request, **serializer.validated_data
        )
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)


class ProcessTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ProcessTypeSerializer
    permission_classes = [ProcessTypePermission]
    pagination_class = None

    def get_queryset(self):
        queryset = ProcessType.objects.all()
        return queryset if self.request.user.is_superuser else queryset.filter(active=True)
