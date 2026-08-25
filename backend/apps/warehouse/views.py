from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import StockMovement, WarehouseStock
from .reporting import build_warehouse_report_workbook
from .serializers import (
    StockMovementSerializer,
    WarehouseReportFilterSerializer,
    WarehouseStockSerializer,
)


class WarehouseStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WarehouseStockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = WarehouseStock.objects.filter(
            company=self.request.user.company,
            product__is_stock_item=True,
            product__is_archived=False,
        ).select_related('product', 'product__category', 'product__unit', 'product__supplier')
        search = self.request.query_params.get('search', '').strip()
        category_id = self.request.query_params.get('category')
        supplier_id = self.request.query_params.get('supplier')
        only_available = self.request.query_params.get('only_available')
        if search:
            queryset = queryset.filter(
                Q(product__name__icontains=search) |
                Q(product__sku__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        if supplier_id:
            queryset = queryset.filter(product__supplier_id=supplier_id)
        if only_available in ('1', 'true', 'True'):
            queryset = queryset.filter(quantity_on_hand__gt=0)
        return queryset.order_by('product__name', 'product__sku')


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = StockMovement.objects.filter(
            company=self.request.user.company,
            product__is_stock_item=True,
        ).select_related('product', 'product__category', 'product__unit', 'product__supplier', 'created_by')
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset


class WarehouseReportExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = WarehouseReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        buffer = build_warehouse_report_workbook(
            request.user.company,
            serializer.validated_data,
        )
        filename = f'warehouse_report_{timezone.localdate():%Y%m%d}.xlsx'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type=(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        )
