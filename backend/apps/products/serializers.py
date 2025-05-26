from rest_framework import serializers
from .models import Product, ProductCategory, Unit, ProductChangeLog, GlobalSettings
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


class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = '__all__'


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
        )
