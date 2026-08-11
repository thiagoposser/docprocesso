from rest_framework.routers import DefaultRouter

from .views import ProcessTypeViewSet, ProcessViewSet

router = DefaultRouter()
router.register("processes", ProcessViewSet, basename="process")
router.register("process-types", ProcessTypeViewSet, basename="process-type")
urlpatterns = router.urls
