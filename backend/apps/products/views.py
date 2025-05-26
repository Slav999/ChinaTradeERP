from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from .models import Product, ProductCategory, Unit, ProductChangeLog, GlobalSettings
from .serializers import ProductSerializer, ProductCategorySerializer, UnitSerializer, ProductChangeLogSerializer, \
    GlobalSettingsSerializer


class ProductViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'sku']

    def get_queryset(self):
        return Product.objects.filter(supplier__company=self.request.user.company)

    def get_serializer_class(self):
        if self.action == 'history':
            return ProductChangeLogSerializer
        return super().get_serializer_class()

    def log_changes(self, old, new):
        fields = [
            'name', 'sku', 'description', 'category_id',
            'unit_id', 'supplier_id', 'quantity',
            'purchase_price', 'sale_price', 'image'
        ]
        for field in fields:
            old_val = getattr(old, field)
            new_val = getattr(new, field)

            if field == 'image':
                old_val = old_val.name if old_val else ''
                new_val = new_val.name if new_val else ''

            if old_val != new_val:
                ProductChangeLog.objects.create(
                    product=new,
                    field_name=field,
                    old_value=str(old_val or ''),
                    new_value=str(new_val or ''),
                    changed_by=self.request.user
                )


class ProductCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer


class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


class GlobalSettingsViewSet(viewsets.ModelViewSet):
    queryset = GlobalSettings.objects.all()
    serializer_class = GlobalSettingsSerializer
