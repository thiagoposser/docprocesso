from rest_framework.routers import DefaultRouter

from .views import OrganizationalFunctionViewSet, OrganizationalUnitViewSet, SectorViewSet, UserSectorMembershipViewSet

router = DefaultRouter()
router.register("organizational-functions", OrganizationalFunctionViewSet, basename="organizational-function")
router.register("units", OrganizationalUnitViewSet, basename="organizational-unit")
router.register("sectors", SectorViewSet, basename="sector")
router.register("user-sector-memberships", UserSectorMembershipViewSet, basename="user-sector-membership")
urlpatterns = router.urls
