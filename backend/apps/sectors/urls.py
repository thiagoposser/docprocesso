from rest_framework.routers import DefaultRouter

from .views import OrganizationalUnitViewSet, SectorViewSet, UserSectorMembershipViewSet

router = DefaultRouter()
router.register("units", OrganizationalUnitViewSet, basename="organizational-unit")
router.register("sectors", SectorViewSet, basename="sector")
router.register("user-sector-memberships", UserSectorMembershipViewSet, basename="user-sector-membership")
urlpatterns = router.urls
