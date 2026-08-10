from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "read", "type", "level"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Notification.objects.available().filter(user=self.request.user)
        params = self.request.query_params
        if params.get("read") in {"true", "false"}:
            queryset = queryset.filter(read=params["read"] == "true")
        if params.get("type"):
            queryset = queryset.filter(type=params["type"])
        if params.get("level"):
            queryset = queryset.filter(level=params["level"])
        for parameter, lookup in (("date_from", "created_at__date__gte"), ("date_to", "created_at__date__lte")):
            if params.get(parameter):
                value = parse_date(params[parameter])
                if not value:
                    raise ValidationError({parameter: "Use uma data no formato YYYY-MM-DD."})
                queryset = queryset.filter(**{lookup: value})
        return queryset

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.read:
            notification.read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["read", "read_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(read=False).update(read=True, read_at=timezone.now())
        return Response({"updated": updated}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(read=False).count()})
