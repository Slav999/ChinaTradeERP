from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupplierOrderViewSet, SupplierOrderStatusViewSet, SupplierOrderItemViewSet

router = DefaultRouter()
router.register(r'supplier-order', SupplierOrderViewSet)
router.register(r'supplier-order-statuses', SupplierOrderStatusViewSet)
router.register(r'supplier-order-items', SupplierOrderItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]