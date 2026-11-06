from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    WriteOffReportExportView,
    StockControlDismissView,
    StockControlExportView,
    StockControlGenerateView,
    StockControlLatestView,
    StockControlLiveExportView,
    StockControlLiveView,
    StockAlertDismissView,
    StockAlertListView,
    NotificationFeedView,
    NotificationHideView,
    NotificationReadAllView,
    NotificationReadView,
    StockMovementViewSet,
    WarehouseReportExportView,
    WarehouseReportSummaryView,
    WarehouseStockViewSet,
)


router = DefaultRouter()
router.register(r'warehouse-stocks', WarehouseStockViewSet, basename='warehouse-stocks')
router.register(r'warehouse-movements', StockMovementViewSet, basename='warehouse-movements')

urlpatterns = [
    path('warehouse-write-offs/export/', WriteOffReportExportView.as_view(), name='warehouse-write-offs-export'),
    path('warehouse-stock-control/latest/', StockControlLatestView.as_view(), name='warehouse-stock-control-latest'),
    path('warehouse-stock-control/live/', StockControlLiveView.as_view(), name='warehouse-stock-control-live'),
    path('warehouse-stock-control/live/export/', StockControlLiveExportView.as_view(), name='warehouse-stock-control-live-export'),
    path('warehouse-stock-control/generate/', StockControlGenerateView.as_view(), name='warehouse-stock-control-generate'),
    path('warehouse-stock-control/<int:pk>/dismiss/', StockControlDismissView.as_view(), name='warehouse-stock-control-dismiss'),
    path('warehouse-stock-control/<int:pk>/export/', StockControlExportView.as_view(), name='warehouse-stock-control-export'),
    path('warehouse-stock-alerts/', StockAlertListView.as_view(), name='warehouse-stock-alert-list'),
    path('warehouse-stock-alerts/<int:pk>/dismiss/', StockAlertDismissView.as_view(), name='warehouse-stock-alert-dismiss'),
    path('notifications/', NotificationFeedView.as_view(), name='notification-feed'),
    path('notifications/read/', NotificationReadView.as_view(), name='notification-read'),
    path('notifications/read-all/', NotificationReadAllView.as_view(), name='notification-read-all'),
    path('notifications/hide/', NotificationHideView.as_view(), name='notification-hide'),
    path('warehouse-report/export/', WarehouseReportExportView.as_view(), name='warehouse-report-export'),
    path('warehouse-report/summary/', WarehouseReportSummaryView.as_view(), name='warehouse-report-summary'),
    path('', include(router.urls)),
]
