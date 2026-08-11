from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_date
from rest_framework import filters, mixins, viewsets
from rest_framework.exceptions import ValidationError

from apps.audit.mixins import AuditedWriteMixin

from .models import Payment, PaymentStatus, Supplier
from .permissions import PaymentPermission, SupplierPermission
from .serializers import PaymentSerializer, SupplierSerializer


class SupplierViewSet(AuditedWriteMixin, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [SupplierPermission]
    queryset = Supplier.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "active", "created_at", "updated_at"]
    ordering = ["name", "id"]
    audit_label = "fornecedor"
    audit_fields = ("name", "active")


class PaymentViewSet(AuditedWriteMixin, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [PaymentPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "supplier__name", "process__number", "process__title"]
    ordering_fields = ["due_date", "amount", "status", "created_at", "updated_at"]
    ordering = ["due_date", "id"]
    audit_label = "pagamento"
    audit_fields = ("process", "sector", "supplier", "description", "due_date", "status")

    def get_queryset(self):
        queryset = Payment.objects.select_related("process", "document", "sector", "supplier", "created_by", "paid_by")
        user = self.request.user
        if not user.is_superuser:
            sector_ids = user.sector_memberships.filter(active=True, sector__active=True).values_list("sector_id", flat=True)
            queryset = queryset.filter(sector_id__in=sector_ids)
        params = self.request.query_params
        for parameter, field in {"sector": "sector_id", "supplier": "supplier_id"}.items():
            if params.get(parameter):
                try: queryset = queryset.filter(**{field: int(params[parameter])})
                except ValueError as error: raise ValidationError({parameter: "Informe um ID inteiro válido."}) from error
        if params.get("status"):
            if params["status"] not in PaymentStatus.values: raise ValidationError({"status": "Informe um status válido."})
            queryset = queryset.filter(status=params["status"])
        for parameter, lookup in {"due_from": "due_date__gte", "due_to": "due_date__lte"}.items():
            if params.get(parameter):
                value = parse_date(params[parameter])
                if value is None: raise ValidationError({parameter: "Use uma data no formato YYYY-MM-DD."})
                queryset = queryset.filter(**{lookup: value})
        for parameter, lookup in {"min_amount": "amount__gte", "max_amount": "amount__lte"}.items():
            if params.get(parameter):
                try: value = Decimal(params[parameter])
                except InvalidOperation as error: raise ValidationError({parameter: "Informe um valor decimal válido."}) from error
                queryset = queryset.filter(**{lookup: value})
        return queryset
