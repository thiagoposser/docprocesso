from rest_framework.routers import DefaultRouter

from .views import AttachmentViewSet, DocumentCategoryViewSet, DocumentViewSet

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("attachments", AttachmentViewSet, basename="attachment")
router.register("document-categories", DocumentCategoryViewSet, basename="document-category")
urlpatterns = router.urls
