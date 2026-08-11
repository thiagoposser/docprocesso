from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from django.http import FileResponse, Http404
from django.db.models import Q
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from django.utils.dateparse import parse_date

from .models import Attachment, Document, DocumentCategory, DocumentRole
from .permissions import AttachmentPermission, CategoryPermission, DocumentPermission, can_access_process_document
from .serializers import AttachmentSerializer, DocumentCategorySerializer, DocumentSerializer, ProcessDocumentSerializer
from .services import create_attachment, deactivate_attachment
from apps.audit.mixins import AuditedWriteMixin
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.notifications.models import NotificationLevel, NotificationType
from apps.notifications.services import NotificationService


def is_administrator(user):
    return user.is_staff or user.has_perm("documents.manage_document")


def secure_file_response(file, *, filename, inline=False):
    response = FileResponse(file, as_attachment=not inline, filename=filename or None)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    response["Content-Security-Policy"] = "sandbox"
    return response


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
        queryset = Document.objects.select_related(
            "category", "created_by", "process", "process__current_sector", "process__origin_sector"
        ).prefetch_related("attachments")
        queryset = queryset.exclude(role=DocumentRole.PAYMENT_RECEIPT)
        if not is_administrator(self.request.user):
            queryset = queryset.filter(active=True, category__active=True)
        if not self.request.user.is_superuser:
            sector_ids = self.request.user.sector_memberships.filter(active=True, sector__active=True).values_list("sector_id", flat=True)
            process_filter = Q(process__current_sector_id__in=sector_ids) | Q(
                process__current_sector__isnull=True, process__origin_sector_id__in=sector_ids
            )
            if self.request.user.has_perm("documents.view_document") and self.request.user.has_perm("processes.view_administrativeprocess"):
                queryset = queryset.filter(Q(process__isnull=True) | process_filter)
            else:
                queryset = queryset.filter(process__isnull=True)
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
        if document.process_id:
            from apps.processes.event_services import append_process_event
            from apps.processes.models import ProcessEventType
            append_process_event(
                process=document.process, event_type=ProcessEventType.DOCUMENT_CHANGED,
                title="Documento atualizado", actor=self.request.user,
                payload={"document_id": document.pk},
            )

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
        return secure_file_response(
            document.file.open("rb"), filename=document.original_file_name,
            inline=request.query_params.get("attachment") != "true",
        )

    @action(detail=True, methods=["get", "post"], url_path="attachments")
    def attachments(self, request, pk=None):
        document = self.get_object()
        if request.method == "GET":
            if not request.user.has_perm("documents.view_attachment"):
                self.permission_denied(request)
            items = document.attachments.select_related("created_by").all()
            return Response(AttachmentSerializer(items, many=True, context=self.get_serializer_context()).data)
        if not request.user.has_perm("documents.add_attachment") or not can_access_process_document(
            request.user, document, document_permission="documents.change_document"
        ):
            self.permission_denied(request)
        serializer = AttachmentSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        try:
            attachment = create_attachment(
                document=document, actor=request.user, request=request, **serializer.validated_data
            )
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict if hasattr(error, "message_dict") else error.messages) from error
        return Response(AttachmentSerializer(attachment, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)


class AttachmentViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [AttachmentPermission]
    http_method_names = ["get", "patch", "head", "options"]
    queryset = Attachment.objects.select_related(
        "document", "document__process", "document__process__current_sector", "document__process__origin_sector", "created_by"
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        sector_ids = self.request.user.sector_memberships.filter(active=True, sector__active=True).values_list("sector_id", flat=True)
        process_filter = Q(document__process__current_sector_id__in=sector_ids) | Q(
            document__process__current_sector__isnull=True,
            document__process__origin_sector_id__in=sector_ids,
        )
        queryset = queryset.filter(Q(document__process__isnull=True) | process_filter)
        if not (
            self.request.user.has_perm("payments.view_financial_data")
            and self.request.user.has_perm("payments.view_payment")
            and self.request.user.has_perm("processes.view_administrativeprocess")
        ):
            queryset = queryset.filter(payment_receipt__isnull=True)
        return queryset.distinct()

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        if not attachment.active:
            raise Http404
        record_audit(
            action=AuditAction.DOCUMENT_DOWNLOAD, description="Anexo baixado", request=request,
            entity=attachment, new_values={"document_id": attachment.document_id},
        )
        if attachment.file:
            return secure_file_response(attachment.file.open("rb"), filename=attachment.original_file_name)
        return Response({"external_url": attachment.external_url})

    @action(detail=True, methods=["patch"])
    def deactivate(self, request, pk=None):
        attachment = deactivate_attachment(attachment=self.get_object(), actor=request.user, request=request)
        return Response(self.get_serializer(attachment).data)


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
