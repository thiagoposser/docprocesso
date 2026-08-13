from rest_framework.routers import DefaultRouter

from .views import AdministrativeWorkflowViewSet, ProcessTypeViewSet, ProcessViewSet, WorkflowStageViewSet

router = DefaultRouter()
router.register("processes", ProcessViewSet, basename="process")
router.register("process-types", ProcessTypeViewSet, basename="process-type")
router.register("workflows", AdministrativeWorkflowViewSet, basename="workflow")
router.register("workflow-stages", WorkflowStageViewSet, basename="workflow-stage")
urlpatterns = router.urls
