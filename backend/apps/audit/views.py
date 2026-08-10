from django.utils.dateparse import parse_date
from rest_framework import filters, mixins, viewsets
from rest_framework.exceptions import ValidationError

from .models import AuditLog
from .permissions import CanViewAuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [CanViewAuditLog]
    queryset = AuditLog.objects.select_related("user")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "entity_type", "entity_id", "user__username", "user__first_name", "user__last_name"]
    ordering_fields = ["created_at", "action", "entity_type", "request_method"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("user"):
            queryset = queryset.filter(user_id=params["user"])
        if params.get("action"):
            queryset = queryset.filter(action=params["action"])
        if params.get("entity"):
            queryset = queryset.filter(entity_type__icontains=params["entity"])
        if params.get("method"):
            queryset = queryset.filter(request_method=params["method"].upper())
        for parameter, lookup in (("date_from", "created_at__date__gte"), ("date_to", "created_at__date__lte")):
            if params.get(parameter):
                parsed = parse_date(params[parameter])
                if not parsed:
                    raise ValidationError({parameter: "Use uma data no formato YYYY-MM-DD."})
                queryset = queryset.filter(**{lookup: parsed})
        return queryset
