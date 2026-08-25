from rest_framework import serializers
from django.db import transaction
from django_countries import countries
from .models import CompanySettings, Product, ProductCategory, Unit, ProductChangeLog
from counterparties.models import Counterparty
from core.serializers import ChangeLogBaseSerializer, AuditFieldsMixinSerializer
from counterparties.serializers import CounterpartySerializer
from users.company_defaults import company_defaults_for_country


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'
        read_only_fields = ('company',)

    def validate_name(self, value):
        name = value.strip()
        request = self.context.get('request')
        queryset = ProductCategory.objects.filter(name__iexact=name)
        if request and request.user.is_authenticated:
            queryset = queryset.filter(company=request.user.company)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Category already exists.')
        return name


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'
        read_only_fields = ('company',)

    def validate_name(self, value):
        name = value.strip()
        request = self.context.get('request')
        queryset = Unit.objects.filter(name__iexact=name)
        if request and request.user.is_authenticated:
            queryset = queryset.filter(company=request.user.company)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Unit already exists.')
        return name


class ProductChangeLogSerializer(ChangeLogBaseSerializer):
    class Meta(ChangeLogBaseSerializer.Meta):
        model = ProductChangeLog


class CompanySettingsSerializer(serializers.ModelSerializer):
    business_country = serializers.ChoiceField(choices=countries, required=False, write_only=True)
    company_business_country = serializers.SerializerMethodField()
    company_business_country_name = serializers.SerializerMethodField()
    company_currency_code = serializers.CharField(source='company.base_currency_code', read_only=True)
    company_currency_symbol = serializers.CharField(source='company.base_currency_symbol', read_only=True)
    company_logo = serializers.ImageField(required=False, allow_null=True, write_only=True)
    company_logo_url = serializers.SerializerMethodField()
    company_work_email = serializers.EmailField(required=False, allow_blank=True)
    company_phone = serializers.CharField(required=False, allow_blank=True)
    company_address = serializers.CharField(required=False, allow_blank=True)
    company_bank_details = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CompanySettings
        fields = (
            'id', 'company', 'business_country', 'company_business_country',
            'company_business_country_name', 'company_currency_code', 'company_currency_symbol',
            'company_logo', 'company_logo_url', 'company_work_email', 'company_phone',
            'company_address', 'company_bank_details',
            'cny_to_local_rate', 'usd_to_local_rate', 'logistics_cost_per_kg_usd',
            'internal_logistics_pct', 'retail_tax_pct', 'acquiring_pct', 'packaging_pct', 'margin_pct',
            'settings_confirmed_at',
        )
        read_only_fields = (
            'id', 'company', 'company_business_country', 'company_business_country_name',
            'company_currency_code', 'company_currency_symbol', 'company_logo_url', 'settings_confirmed_at',
        )

    def get_company_business_country(self, obj):
        return str(obj.company.business_country) if obj.company_id else ''

    def get_company_business_country_name(self, obj):
        if not obj.company_id or not obj.company.business_country:
            return ''
        return obj.company.business_country.name

    def get_company_logo_url(self, obj):
        if not obj.company_id or not obj.company.logo:
            return ''
        request = self.context.get('request')
        url = obj.company.logo.url
        return request.build_absolute_uri(url) if request else url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        company = instance.company
        data['company_work_email'] = company.work_email
        data['company_phone'] = company.phone
        data['company_address'] = company.address
        data['company_bank_details'] = company.bank_details
        return data

    def update(self, instance, validated_data):
        with transaction.atomic():
            business_country = validated_data.pop('business_country', None)
            company_logo = validated_data.pop('company_logo', None)
            company_fields = {
                'work_email': validated_data.pop('company_work_email', None),
                'phone': validated_data.pop('company_phone', None),
                'address': validated_data.pop('company_address', None),
                'bank_details': validated_data.pop('company_bank_details', None),
            }
            country_changed = False
            company_update_fields = []
            company = instance.company
            for field, value in company_fields.items():
                if value is not None:
                    setattr(company, field, value)
                    company_update_fields.append(field)
            if company_logo is not None:
                company.logo = company_logo
                company_update_fields.append('logo')
            if business_country:
                defaults = company_defaults_for_country(business_country)
                country_changed = str(company.business_country) != defaults['business_country']
                company.apply_country_defaults(defaults['business_country'])
                company_update_fields.extend([
                    'business_country',
                    'base_currency_code',
                    'base_currency_symbol',
                    'locale_code',
                ])
                if country_changed:
                    validated_data.pop('cny_to_local_rate', None)
                    validated_data.pop('usd_to_local_rate', None)
                if 'retail_tax_pct' not in validated_data:
                    validated_data['retail_tax_pct'] = defaults['retail_tax_pct']
            if company_update_fields:
                company.save(update_fields=list(dict.fromkeys(company_update_fields)))
            instance = super().update(instance, validated_data)
            if business_country and country_changed:
                from .currency import refresh_company_rates

                if not refresh_company_rates(instance.company, instance, require_all=True):
                    raise serializers.ValidationError({
                        'business_country': (
                            'Country was not changed because exchange rates could not be updated. '
                            'Please try again later.'
                        )
                    })
                instance.refresh_from_db()
            return instance


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
    has_history = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = (
            'id',
            'company',
            'created_at',
            'updated_at',
            'created_by',
            'updated_by',
            'is_archived',
            'archived_at',
            'archived_by',
        )

    def validate(self, attrs):
        request = self.context.get('request')
        supplier = attrs.get('supplier', getattr(self.instance, 'supplier', None))
        category = attrs.get('category', getattr(self.instance, 'category', None))
        unit = attrs.get('unit', getattr(self.instance, 'unit', None))
        company = request.user.company if request and request.user.is_authenticated else None
        if company and supplier and supplier.company_id != company.id:
            raise serializers.ValidationError({'supplier_id': 'Selected supplier is not available for your company.'})
        if company and category and category.company_id != company.id:
            raise serializers.ValidationError({'category_id': 'Selected category is not available for your company.'})
        if company and unit and unit.company_id != company.id:
            raise serializers.ValidationError({'unit_id': 'Selected unit is not available for your company.'})
        if supplier and not supplier.is_supplier:
            raise serializers.ValidationError({'supplier_id': 'Selected counterparty is not marked as a supplier.'})
        return attrs

    def get_has_history(self, obj):
        return (
            obj.customer_order_items.exists()
            or obj.supplier_order_items.exists()
            or obj.stock_movements.exists()
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            company = request.user.company
            self.fields['category_id'].queryset = ProductCategory.objects.filter(company=company)
            self.fields['unit_id'].queryset = Unit.objects.filter(company=company)
            self.fields['supplier_id'].queryset = Counterparty.objects.filter(company=company, is_supplier=True)

    def _calculate_sale_price(self, product):
        if not product.weight_kg or product.weight_kg <= 0:
            product.sale_price = 0
            product.save(update_fields=['sale_price'])
            return product
        try:
            settings = product.supplier.company.product_settings
        except CompanySettings.DoesNotExist:
            settings = CompanySettings.objects.create(
                company=product.supplier.company,
                **CompanySettings.default_values(product.supplier.company.business_country),
            )
        product.sale_price = product.calculate_sale_price(settings)
        product.save(update_fields=['sale_price'])
        return product

    def create(self, validated_data):
        product = super().create(validated_data)
        product = self._calculate_sale_price(product)
        from warehouse.services import ensure_stock_for_product

        ensure_stock_for_product(product)
        return product

    def update(self, instance, validated_data):
        product = super().update(instance, validated_data)
        product = self._calculate_sale_price(product)
        from warehouse.services import ensure_stock_for_product

        ensure_stock_for_product(product)
        return product


class ProductSupplierSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Counterparty
        fields = ('id', 'name')


class ProductListSerializer(AuditFieldsMixinSerializer, serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)
    unit = UnitSerializer(read_only=True)
    supplier = ProductSupplierSummarySerializer(read_only=True)
    archived_by = serializers.StringRelatedField(read_only=True)
    has_history = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'sku', 'category', 'unit', 'supplier',
            'quantity', 'is_stock_item', 'purchase_price', 'sale_price', 'image',
            'units_per_package', 'weight_kg', 'length_m', 'width_m', 'height_m',
            'is_archived', 'archived_at', 'archived_by', 'has_history',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        )

    def get_has_history(self, obj):
        return (
            obj.customer_order_items.exists()
            or obj.supplier_order_items.exists()
            or obj.stock_movements.exists()
        )
