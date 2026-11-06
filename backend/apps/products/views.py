from django.utils import timezone
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from core.pagination import StandardResultsSetPagination
from .models import CompanySettings, Product, ProductCategory, Unit, ProductChangeLog
from .serializers import ProductSerializer, ProductCategorySerializer, UnitSerializer, ProductChangeLogSerializer, \
    CompanySettingsSerializer, ProductListSerializer
from .currency import refresh_company_rates
from users.permissions import HasCompanyAccessPermission


class ProductViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated, HasCompanyAccessPermission]
    access_view_permission = 'products.view'
    access_manage_permission = 'products.manage'

    def get_queryset(self):
        queryset = Product.objects.filter(
            company=self.request.user.company
        ).select_related('category', 'unit', 'supplier')
        if self.action == 'list':
            archive_status = self.request.query_params.get('archive_status', 'active')
            if archive_status == 'archived':
                queryset = queryset.filter(is_archived=True)
            elif archive_status == 'all':
                pass
            else:
                queryset = queryset.filter(is_archived=False)

        search = self.request.query_params.get('search', '').strip()
        category_id = self.request.query_params.get('category')
        category_query = self.request.query_params.get('category_query', '').strip()
        supplier_query = self.request.query_params.get('supplier_query', '').strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if category_query:
            queryset = queryset.filter(category__name__icontains=category_query)
        if supplier_query:
            queryset = queryset.filter(supplier__name__icontains=supplier_query)

        return queryset.order_by('-created_at', '-id')

    def product_has_history(self, product):
        from customer_orders.models import CustomerOrderItem
        from supplier_orders.models import SupplierOrderItem
        from warehouse.models import StockMovement

        return (
            CustomerOrderItem.objects.filter(product=product).exists()
            or SupplierOrderItem.objects.filter(product=product).exists()
            or StockMovement.objects.filter(product=product).exists()
        )

    def log_archive_change(self, product, old_value, new_value):
        ProductChangeLog.objects.create(
            product=product,
            field_name='is_archived',
            old_value=old_value,
            new_value=new_value,
            changed_by=self.request.user,
        )

    def get_serializer_class(self):
        if self.action == 'history':
            return ProductChangeLogSerializer
        if self.action == 'list':
            return ProductListSerializer
        return super().get_serializer_class()

    def log_changes(self, old, new):
        fields = [
            'name', 'sku', 'description', 'category_id',
            'unit_id', 'supplier_id', 'quantity', 'is_stock_item',
            'purchase_price', 'sale_price', 'sale_price_mode', 'image'
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
        if not self.product_has_history(instance):
            instance.delete()
            return

        instance.is_archived = True
        instance.archived_at = timezone.now()
        instance.archived_by = self.request.user
        instance.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'updated_at'])
        self.log_archive_change(instance, 'False', 'True')

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        product = self.get_object()
        if not product.is_archived:
            product.is_archived = True
            product.archived_at = timezone.now()
            product.archived_by = request.user
            product.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'updated_at'])
            self.log_archive_change(product, 'False', 'True')
        serializer = self.get_serializer(product)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        product = self.get_object()
        if not product.is_archived:
            serializer = self.get_serializer(product)
            return Response(serializer.data)

        product.is_archived = False
        product.archived_at = None
        product.archived_by = None
        product.save(update_fields=['is_archived', 'archived_at', 'archived_by', 'updated_at'])
        self.log_archive_change(product, 'True', 'False')
        serializer = self.get_serializer(product)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='permanent-delete')
    def permanent_delete(self, request, pk=None):
        if not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can permanently delete products.')

        product = self.get_object()
        if self.product_has_history(product):
            return Response(
                {'detail': 'Product is used by orders or warehouse movements and cannot be permanently deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated, HasCompanyAccessPermission]
    access_view_permission = 'products.view'
    access_manage_permission = 'products.manage'

    def get_queryset(self):
        return ProductCategory.objects.filter(company=self.request.user.company).order_by('name')

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ('PUT', 'PATCH', 'DELETE') and not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can edit or delete product categories.')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def perform_update(self, serializer):
        category = serializer.save()
        self.recalculate_category_products(category)

    def recalculate_category_products(self, category):
        try:
            settings = category.company.product_settings
        except CompanySettings.DoesNotExist:
            settings = CompanySettings.objects.create(
                company=category.company,
                **CompanySettings.default_values(category.company.business_country),
            )

        for product in Product.objects.filter(
            company=category.company,
            category=category,
            sale_price_mode=Product.SALE_PRICE_MODE_AUTOMATIC,
        ).select_related('category', 'supplier'):
            product.sale_price = product.calculate_sale_price(settings)
            product.save(update_fields=['sale_price'])

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can delete product categories.')

        instance = self.get_object()
        if Product.objects.filter(company=request.user.company, category=instance, is_archived=False).exists():
            return Response(
                {'detail': 'Category is used by active products and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated, HasCompanyAccessPermission]
    access_view_permission = 'products.view'
    access_manage_permission = 'products.manage'

    def get_queryset(self):
        return Unit.objects.filter(company=self.request.user.company).order_by('name')

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ('PUT', 'PATCH', 'DELETE') and not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can edit or delete product units.')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can delete product units.')

        instance = self.get_object()
        if Product.objects.filter(company=request.user.company, unit=instance, is_archived=False).exists():
            return Response(
                {'detail': 'Unit is used by active products and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


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
            defaults=CompanySettings.default_values(self.request.user.company.business_country),
        )
        if (
            self.request.user.is_company_admin
            and settings.rates_updated_at is None
            and settings.cny_to_local_rate == CompanySettings.default_values()['cny_to_local_rate']
            and settings.usd_to_local_rate == CompanySettings.default_values()['usd_to_local_rate']
        ):
            refresh_company_rates(self.request.user.company, settings)
            settings.refresh_from_db()
        return settings

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_company_settings())
        return Response([serializer.data])

    def create(self, request, *args, **kwargs):
        settings = self.get_company_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        settings = serializer.save(settings_confirmed_at=timezone.now())
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
