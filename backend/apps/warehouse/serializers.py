from rest_framework import serializers

from products.serializers import ProductListSerializer
from .models import StockMovement, WarehouseStock


class WarehouseStockSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    quantity_available = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = WarehouseStock
        fields = (
            'id', 'product', 'quantity_on_hand', 'quantity_reserved',
            'quantity_expected', 'quantity_available', 'updated_at',
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


class WarehouseReportFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=255)
    supplier = serializers.IntegerField(required=False, min_value=1)
    category = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError({
                'date_to': 'End date must be on or after start date.',
            })
        if 'search' in attrs:
            attrs['search'] = attrs['search'].strip()
        return attrs
