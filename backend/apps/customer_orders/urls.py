from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerOrderViewSet, CustomerOrderStatusViewSet, CustomerOrderItemViewSet

router = DefaultRouter()
router.register(r'customer-order', CustomerOrderViewSet)
router.register(r'customer-order-statuses', CustomerOrderStatusViewSet)
router.register(r'customer-order-items', CustomerOrderItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]