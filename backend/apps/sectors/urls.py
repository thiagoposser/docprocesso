from rest_framework.routers import DefaultRouter

from .views import SectorViewSet, UserSectorMembershipViewSet

router = DefaultRouter()
router.register("sectors", SectorViewSet, basename="sector")
router.register("user-sector-memberships", UserSectorMembershipViewSet, basename="user-sector-membership")
urlpatterns = router.urls
