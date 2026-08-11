from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_date
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.audit.mixins import AuditedWriteMixin

from .deadline_services import generate_deadline_notifications
from .models import Payment, PaymentStatus, Supplier
from .permissions import PaymentPermission, SupplierPermission
from .serializers import PaymentCancelSerializer, PaymentConfirmSerializer, PaymentReceiptSerializer, PaymentReceiptUploadSerializer, PaymentScheduleSerializer, PaymentSerializer, SupplierSerializer
from .services import InvalidPaymentTransition, PaymentAccessDenied, PaymentConflictError, cancel_payment, confirm_payment, create_payment_receipt, schedule_payment


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

    def get_serializer_class(self):
        return {
            "schedule": PaymentScheduleSerializer,
            "confirm": PaymentConfirmSerializer,
            "cancel": PaymentCancelSerializer,
            "receipts": PaymentReceiptUploadSerializer if self.request.method == "POST" else PaymentReceiptSerializer,
        }.get(self.action, PaymentSerializer)

    def get_queryset(self):
        queryset = Payment.objects.select_related("process", "document", "sector", "supplier", "created_by", "paid_by")
        user = self.request.user
        if not user.is_superuser:
            sector_ids = user.sector_memberships.filter(active=True, sector__active=True).values_list("sector_id", flat=True)
            queryset = queryset.filter(sector_id__in=sector_ids)
        params = self.request.query_params
        for parameter, field in {"sector": "sector_id", "supplier": "supplier_id", "process": "process_id"}.items():
            if params.get(parameter):
                try: queryset = queryset.filter(**{field: int(params[parameter])})
                except ValueError as error: raise ValidationError({parameter: "Informe um ID inteiro válido."}) from error
        if params.get("status"):
            if params["status"] not in PaymentStatus.values: raise ValidationError({"status": "Informe um status válido."})
            queryset = queryset.filter(status=params["status"])
        if params.get("deadline"):
            try:
                queryset = queryset.with_deadline(params["deadline"])
            except ValueError as error:
                raise ValidationError({"deadline": "Use overdue, today ou upcoming."}) from error
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

    @action(detail=False, methods=["get"], url_path="deadline-summary")
    def deadline_summary(self, request):
        generate_deadline_notifications(user=request.user)
        queryset = self.get_queryset()
        return Response({
            deadline: queryset.with_deadline(deadline).count()
            for deadline in ("overdue", "today", "upcoming")
        })

    def _execute_action(self, request, service):
        payment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = service(payment_id=payment.pk, actor=request.user, **serializer.validated_data)
        except PaymentConflictError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except PaymentAccessDenied as error:
            raise PermissionDenied(str(error)) from error
        except InvalidPaymentTransition as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(PaymentSerializer(updated, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        return self._execute_action(request, schedule_payment)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._execute_action(request, confirm_payment)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._execute_action(request, cancel_payment)

    @action(detail=True, methods=["get", "post"])
    def receipts(self, request, pk=None):
        payment = self.get_object()
        if request.method == "GET":
            queryset = payment.receipts.select_related("attachment", "attachment__created_by", "created_by")
            return Response(PaymentReceiptSerializer(queryset, many=True, context=self.get_serializer_context()).data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            receipt = create_payment_receipt(
                payment_id=payment.pk, actor=request.user, upload=serializer.validated_data["file"], request=request,
            )
        except PaymentAccessDenied as error:
            raise PermissionDenied(str(error)) from error
        except InvalidPaymentTransition as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(PaymentReceiptSerializer(receipt, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)
