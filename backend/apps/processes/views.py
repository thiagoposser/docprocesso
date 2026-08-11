from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import filters, mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import AdministrativeProcess, ProcessStatus, ProcessType
from .permissions import ProcessPermission, ProcessTypePermission
from .serializers import ProcessDetailSerializer, ProcessListSerializer, ProcessTypeSerializer, ProcessWriteSerializer


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


class ProcessTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ProcessTypeSerializer
    permission_classes = [ProcessTypePermission]
    pagination_class = None

    def get_queryset(self):
        queryset = ProcessType.objects.all()
        return queryset if self.request.user.is_superuser else queryset.filter(active=True)
