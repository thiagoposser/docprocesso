from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.sectors.policies import can_access_sector


def process_sector(document):
    process = document.process
    return process.current_sector or process.origin_sector


def can_access_process_document(user, document, *, document_permission):
    if document.process_id is None:
        return True
    return user.has_perm(document_permission) and can_access_sector(
        user,
        permission="processes.view_administrativeprocess",
        sector=process_sector(document),
    )


class DocumentPermission(BasePermission):
    message = "Você não possui permissão para gerenciar documentos."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if view.action == "attachments":
            return request.user.has_perm("documents.add_attachment")
        if view.action in {"partial_update", "update"} and request.user.has_perm("documents.change_document"):
            return True
        return request.user.is_staff or request.user.has_perm("documents.manage_document")

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            permission = "documents.view_document"
        else:
            permission = "documents.change_document"
        if obj.process_id is None:
            return request.method in SAFE_METHODS or request.user.is_staff or request.user.has_perm("documents.manage_document")
        return can_access_process_document(request.user, obj, document_permission=permission)


class AttachmentPermission(BasePermission):
    message = "Você não possui permissão para acessar este anexo."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        permission = "documents.view_attachment" if view.action in {"retrieve", "download"} else "documents.change_attachment"
        return request.user.has_perm(permission)

    def has_object_permission(self, request, view, obj):
        document_permission = "documents.view_document" if view.action in {"retrieve", "download"} else "documents.change_document"
        return can_access_process_document(request.user, obj.document, document_permission=document_permission)


class CategoryPermission(DocumentPermission):
    pass
