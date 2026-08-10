from rest_framework.permissions import SAFE_METHODS, BasePermission


class DocumentPermission(BasePermission):
    message = "Você não possui permissão para gerenciar documentos."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.has_perm("documents.manage_document")


class CategoryPermission(DocumentPermission):
    pass
