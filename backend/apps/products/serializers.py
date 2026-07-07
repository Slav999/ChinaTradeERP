from rest_framework import serializers
from .models import CompanySettings, Product, ProductCategory, Unit, ProductChangeLog
from counterparties.models import Counterparty
from core.serializers import ChangeLogBaseSerializer, AuditFieldsMixinSerializer
from counterparties.serializers import CounterpartySerializer


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'


class ProductChangeLogSerializer(ChangeLogBaseSerializer):
    class Meta(ChangeLogBaseSerializer.Meta):
        model = ProductChangeLog


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = '__all__'
        read_only_fields = ('id', 'company')


class ProductSerializer(AuditFieldsMixinSerializer, serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductCategory.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )
    unit = UnitSerializer(read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(),
        source='unit',
        write_only=True,
        required=False,
        allow_null=True
    )
    supplier = CounterpartySerializer(read_only=True)
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Counterparty.objects.all(),
        source='supplier',
        write_only=True
    )

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'created_by',
            'updated_by',
            'is_archived',
            'archived_at',
            'archived_by',
        )

    def validate(self, attrs):
        supplier = attrs.get('supplier', getattr(self.instance, 'supplier', None))
        if supplier and not supplier.is_supplier:
            raise serializers.ValidationError({'supplier_id': 'Selected counterparty is not marked as a supplier.'})
        return attrs


class ProductSupplierSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Counterparty
        fields = ('id', 'name')


class ProductListSerializer(AuditFieldsMixinSerializer, serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)
    unit = UnitSerializer(read_only=True)
    supplier = ProductSupplierSummarySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'sku', 'category', 'unit', 'supplier',
            'quantity', 'purchase_price', 'sale_price', 'image',
            'units_per_package', 'weight_kg', 'length_m', 'width_m', 'height_m',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        )
