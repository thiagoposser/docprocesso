from rest_framework.routers import DefaultRouter

from .views import SectorViewSet

router = DefaultRouter()
router.register("sectors", SectorViewSet, basename="sector")
urlpatterns = router.urls
