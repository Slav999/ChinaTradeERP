from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import StockMovementViewSet, WarehouseReportExportView, WarehouseStockViewSet


router = DefaultRouter()
router.register(r'warehouse-stocks', WarehouseStockViewSet, basename='warehouse-stocks')
router.register(r'warehouse-movements', StockMovementViewSet, basename='warehouse-movements')

urlpatterns = [
    path('warehouse-report/export/', WarehouseReportExportView.as_view(), name='warehouse-report-export'),
    path('', include(router.urls)),
]
