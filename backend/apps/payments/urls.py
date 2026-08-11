from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, SupplierViewSet

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("payments", PaymentViewSet, basename="payment")
urlpatterns = router.urls
