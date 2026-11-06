from decimal import Decimal

from rest_framework import serializers

from products.serializers import ProductListSerializer
from .models import StockAlert, StockControlSnapshot, StockMovement, WarehouseStock


class WarehouseStockSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    quantity_available = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    stock_control = serializers.SerializerMethodField()
    quantity_physical = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = WarehouseStock
        fields = (
            'id', 'product', 'quantity_on_hand', 'quantity_reserved',
            'quantity_expected', 'quantity_available', 'updated_at',
            'quantity_defective', 'quantity_physical', 'stock_control',
        )

    def get_stock_control(self, obj):
        if obj.product.minimum_stock_level is None:
            return None
        from .stock_control import (
            automatic_consumption_context,
            company_stock_settings,
            stock_control_item,
        )

        if not hasattr(self, '_stock_control_settings'):
            self._stock_control_settings = company_stock_settings(obj.company)
            self._automatic_consumption_context = automatic_consumption_context(
                obj.company,
                self._stock_control_settings,
            )
        return stock_control_item(
            obj,
            self._stock_control_settings,
            self._automatic_consumption_context,
        )


class StockMovementSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            'id', 'product', 'movement_type', 'movement_type_display', 'quantity',
            'source_type', 'source_id', 'comment', 'created_by', 'created_at',
        )


class WarehouseOperationSerializer(serializers.Serializer):
    ACTION_RELEASE_DEFECT = 'release_defect'
    ACTION_WRITE_OFF_DEFECT = 'write_off_defect'
    ACTION_WRITE_OFF_STOCK = 'write_off_stock'

    action = serializers.ChoiceField(choices=(
        ACTION_RELEASE_DEFECT,
        ACTION_WRITE_OFF_DEFECT,
        ACTION_WRITE_OFF_STOCK,
    ))
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    reason = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=('defect', 'marketing', 'storage_damage', 'inventory_adjustment', 'other'),
    )
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs['action'] == self.ACTION_WRITE_OFF_STOCK and not attrs.get('reason'):
            raise serializers.ValidationError({'reason': 'Select a write-off reason.'})
        return attrs


class StockControlSnapshotSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    is_dismissed = serializers.SerializerMethodField()

    class Meta:
        model = StockControlSnapshot
        fields = (
            'id', 'schedule_date', 'source', 'source_display', 'generated_at',
            'delivery_lead_days', 'timezone_name', 'summary', 'items', 'is_dismissed',
        )

    def get_is_dismissed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        dismissed_user_ids = getattr(obj, '_dismissed_user_ids', None)
        if dismissed_user_ids is not None:
            return request.user.id in dismissed_user_ids
        return obj.dismissals.filter(user=request.user).exists()


class StockAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    sku = serializers.CharField(source='product.sku', read_only=True)
    unit = serializers.CharField(source='product.unit.name', read_only=True, allow_null=True)

    class Meta:
        model = StockAlert
        fields = (
            'id', 'status', 'product_id', 'product_name', 'sku', 'unit',
            'available_quantity', 'minimum_stock_level', 'expected_quantity',
            'recommended_order_quantity', 'created_at',
        )


class WarehouseReportFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=255)
    supplier = serializers.IntegerField(required=False, min_value=1)
    supplier_query = serializers.CharField(required=False, allow_blank=True, max_length=255)
    category = serializers.IntegerField(required=False, min_value=1)
    category_query = serializers.CharField(required=False, allow_blank=True, max_length=255)
    only_available = serializers.BooleanField(required=False)
    product_ids = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    metric = serializers.ChoiceField(
        required=False,
        choices=('quantity', 'total_cny', 'total_local'),
    )
    unit = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate(self, attrs):
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError({
                'date_to': 'End date must be on or after start date.',
            })
        if 'search' in attrs:
            attrs['search'] = attrs['search'].strip()
        if 'supplier_query' in attrs:
            attrs['supplier_query'] = attrs['supplier_query'].strip()
        if 'category_query' in attrs:
            attrs['category_query'] = attrs['category_query'].strip()
        if 'unit' in attrs:
            attrs['unit'] = attrs['unit'].strip()
        if 'product_ids' in attrs:
            attrs['product_ids'] = self._parse_product_ids(attrs['product_ids'])
        return attrs

    def _parse_product_ids(self, value):
        product_ids = []
        for raw_id in value.split(','):
            raw_id = raw_id.strip()
            if not raw_id:
                continue
            if not raw_id.isdigit():
                raise serializers.ValidationError({
                    'product_ids': 'Product ids must be comma-separated integers.',
                })
            product_ids.append(int(raw_id))
        return product_ids
