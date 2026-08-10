from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import action
from django.http import FileResponse, Http404
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from django.utils.dateparse import parse_date

from .models import Document, DocumentCategory
from .permissions import CategoryPermission, DocumentPermission
from .serializers import DocumentCategorySerializer, DocumentSerializer
from apps.audit.mixins import AuditedWriteMixin
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.notifications.models import NotificationLevel, NotificationType
from apps.notifications.services import NotificationService


def is_administrator(user):
    return user.is_staff or user.has_perm("documents.manage_document")


class DocumentViewSet(AuditedWriteMixin, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [DocumentPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "category__name"]
    ordering_fields = ["title", "category__name", "active", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    audit_label = "documento"
    audit_fields = ("title", "description", "category", "external_url", "active")

    def get_queryset(self):
        queryset = Document.objects.select_related("category", "created_by")
        if not is_administrator(self.request.user):
            queryset = queryset.filter(active=True, category__active=True)
        category = self.request.query_params.get("category")
        active = self.request.query_params.get("active")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if category:
            queryset = queryset.filter(category_id=category)
        if active in {"true", "false"} and is_administrator(self.request.user):
            queryset = queryset.filter(active=active == "true")
        if date_from:
            parsed = parse_date(date_from)
            if not parsed:
                raise ValidationError({"date_from": "Use uma data no formato YYYY-MM-DD."})
            queryset = queryset.filter(updated_at__date__gte=parsed)
        if date_to:
            parsed = parse_date(date_to)
            if not parsed:
                raise ValidationError({"date_to": "Use uma data no formato YYYY-MM-DD."})
            queryset = queryset.filter(updated_at__date__lte=parsed)
        return queryset

    def save_audited_create(self, serializer):
        document = serializer.save(created_by=self.request.user)
        NotificationService.create(user=self.request.user, title="Documento criado", message=f'"{document.title}" foi cadastrado com sucesso.', type=NotificationType.DOCUMENT, level=NotificationLevel.SUCCESS, action_url=f"/documentos/{document.pk}")
        return document

    def perform_update(self, serializer):
        owner = serializer.instance.created_by
        super().perform_update(serializer)
        document = serializer.instance
        if owner != self.request.user:
            NotificationService.create(user=owner, title="Documento atualizado", message=f'"{document.title}" foi atualizado.', type=NotificationType.DOCUMENT, level=NotificationLevel.INFO, action_url=f"/documentos/{document.pk}")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        record_audit(action=AuditAction.DOCUMENT_VIEW, description="Documento visualizado", request=request, entity=instance, new_values={"title": instance.title, "category": instance.category.name})
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.file:
            raise Http404
        record_audit(action=AuditAction.DOCUMENT_DOWNLOAD, description="Documento baixado", request=request, entity=document, new_values={"title": document.title, "file_name": document.original_file_name})
        return FileResponse(document.file.open("rb"), as_attachment=request.query_params.get("attachment") == "true", filename=document.original_file_name or None)


class DocumentCategoryViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = DocumentCategorySerializer
    permission_classes = [CategoryPermission]
    queryset = DocumentCategory.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "active", "created_at", "updated_at"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset if is_administrator(self.request.user) else queryset.filter(active=True)
