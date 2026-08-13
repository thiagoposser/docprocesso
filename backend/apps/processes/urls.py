from rest_framework.routers import DefaultRouter

from .views import AdministrativeWorkflowViewSet, ProcessTypeViewSet, ProcessViewSet

router = DefaultRouter()
router.register("processes", ProcessViewSet, basename="process")
router.register("process-types", ProcessTypeViewSet, basename="process-type")
router.register("workflows", AdministrativeWorkflowViewSet, basename="workflow")
urlpatterns = router.urls
