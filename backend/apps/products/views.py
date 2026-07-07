from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from core.pagination import StandardResultsSetPagination
from .models import CompanySettings, Product, ProductCategory, Unit, ProductChangeLog
from .serializers import ProductSerializer, ProductCategorySerializer, UnitSerializer, ProductChangeLogSerializer, \
    CompanySettingsSerializer, ProductListSerializer


class ProductViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Product.objects.filter(
            supplier__company=self.request.user.company
        ).select_related('category', 'unit', 'supplier')
        if self.action == 'list':
            queryset = queryset.filter(is_archived=False)

        search = self.request.query_params.get('search', '').strip()
        category_id = self.request.query_params.get('category')
        supplier_query = self.request.query_params.get('supplier_query', '').strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if supplier_query:
            queryset = queryset.filter(supplier__name__icontains=supplier_query)

        return queryset.order_by('-created_at', '-id')

    def get_serializer_class(self):
        if self.action == 'history':
            return ProductChangeLogSerializer
        if self.action == 'list':
            return ProductListSerializer
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

    def perform_destroy(self, instance):
        instance.is_archived = True
        instance.archived_at = timezone.now()
        instance.archived_by = self.request.user
        instance.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'updated_at'])


class ProductCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer


class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


class CompanySettingsViewSet(viewsets.ModelViewSet):
    queryset = CompanySettings.objects.all()
    serializer_class = CompanySettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CompanySettings.objects.filter(company=self.request.user.company)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can change company settings.')

    def get_company_settings(self):
        settings, _ = CompanySettings.objects.get_or_create(
            company=self.request.user.company,
            defaults=CompanySettings.default_values(),
        )
        return settings

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_company_settings())
        return Response([serializer.data])

    def create(self, request, *args, **kwargs):
        settings = self.get_company_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
