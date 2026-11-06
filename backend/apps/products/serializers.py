from decimal import Decimal

from rest_framework import serializers
import pytz
from django.db import transaction
from django.utils import translation
from django_countries import countries
from .models import CompanySettings, Product, ProductCategory, Unit, ProductChangeLog
from counterparties.models import Counterparty
from core.serializers import ChangeLogBaseSerializer, AuditFieldsMixinSerializer
from counterparties.serializers import CounterpartySerializer
from users.company_defaults import company_defaults_for_country
from users.access import user_has_permission


FINANCIAL_SETTINGS_FIELDS = (
    'cny_to_local_rate',
    'usd_to_local_rate',
    'logistics_cost_per_kg_usd',
    'internal_logistics_pct',
    'retail_tax_pct',
    'acquiring_pct',
    'packaging_pct',
    'margin_pct',
)


class ProductCategorySerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'company.settings.manage'):
            data.pop('margin_pct', None)
        return data

    def validate(self, attrs):
        request = self.context.get('request')
        if request and 'margin_pct' in attrs and not user_has_permission(request.user, 'company.settings.manage'):
            raise serializers.ValidationError({'margin_pct': 'Only a company administrator can change markup.'})
        return attrs

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        permission = None
        if instance.field_name == 'purchase_price':
            permission = 'pricing.purchase.view'
        elif instance.field_name in {'sale_price', 'sale_price_mode'}:
            permission = 'pricing.sale.view'
        if request and permission and not user_has_permission(user, permission):
            data['old_value'] = None
            data['new_value'] = None
        return data


class CompanySettingsSerializer(serializers.ModelSerializer):
    business_country = serializers.ChoiceField(choices=countries, required=False, write_only=True)
    company_business_country = serializers.SerializerMethodField()
    company_business_country_name = serializers.SerializerMethodField()
    company_currency_code = serializers.CharField(source='company.base_currency_code', read_only=True)
    company_currency_symbol = serializers.CharField(source='company.base_currency_symbol', read_only=True)
    company_language_code = serializers.ChoiceField(
        source='company.language_code',
        choices=(('ru', 'Русский'), ('en', 'English')),
        required=False,
    )
    company_logo = serializers.ImageField(required=False, allow_null=True, write_only=True)
    company_logo_url = serializers.SerializerMethodField()
    company_work_email = serializers.EmailField(required=False, allow_blank=True)
    company_phone = serializers.CharField(required=False, allow_blank=True)
    company_address = serializers.CharField(required=False, allow_blank=True)
    company_china_warehouse_address = serializers.CharField(required=False, allow_blank=True)
    company_bank_details = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CompanySettings
        fields = (
            'id', 'company', 'business_country', 'company_business_country',
            'company_business_country_name', 'company_currency_code', 'company_currency_symbol',
            'company_language_code',
            'company_logo', 'company_logo_url', 'company_work_email', 'company_phone',
            'company_address', 'company_china_warehouse_address', 'company_bank_details',
            'cny_to_local_rate', 'usd_to_local_rate', 'logistics_cost_per_kg_usd',
            'internal_logistics_pct', 'retail_tax_pct', 'acquiring_pct', 'packaging_pct', 'margin_pct',
            'stock_delivery_lead_days', 'stock_timezone', 'stock_weekly_control_enabled',
            'stock_notification_weekday', 'stock_notification_time',
            'stock_consumption_history_days',
            'settings_confirmed_at',
        )
        read_only_fields = (
            'id', 'company', 'company_business_country', 'company_business_country_name',
            'company_currency_code', 'company_currency_symbol', 'company_logo_url', 'settings_confirmed_at',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'company.settings.manage'):
            for field_name in FINANCIAL_SETTINGS_FIELDS:
                self.fields.pop(field_name, None)

    def get_company_business_country(self, obj):
        return str(obj.company.business_country) if obj.company_id else ''

    def get_company_business_country_name(self, obj):
        if not obj.company_id or not obj.company.business_country:
            return ''
        request = self.context.get('request')
        requested_language = getattr(getattr(request, 'user', None), 'notification_language', None)
        language = 'en' if requested_language == 'en' else 'ru'
        with translation.override(language):
            return str(obj.company.business_country.name)

    def get_company_logo_url(self, obj):
        if not obj.company_id or not obj.company.logo:
            return ''
        request = self.context.get('request')
        url = obj.company.logo.url
        return request.build_absolute_uri(url) if request else url

    def validate_stock_timezone(self, value):
        if value not in pytz.all_timezones_set:
            raise serializers.ValidationError('Select a valid time zone.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        retail_tax = attrs.get('retail_tax_pct', getattr(self.instance, 'retail_tax_pct', Decimal('0.00')))
        acquiring = attrs.get('acquiring_pct', getattr(self.instance, 'acquiring_pct', Decimal('0.00')))
        if retail_tax + acquiring >= Decimal('1.00'):
            raise serializers.ValidationError({
                'retail_tax_pct': 'Retail tax and acquiring fee must total less than 100%.',
            })
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        company = instance.company
        data['company_work_email'] = company.work_email
        data['company_phone'] = company.phone
        data['company_address'] = company.address
        data['company_china_warehouse_address'] = company.china_warehouse_address
        data['company_bank_details'] = company.bank_details
        return data

    def update(self, instance, validated_data):
        with transaction.atomic():
            business_country = validated_data.pop('business_country', None)
            company_logo = validated_data.pop('company_logo', None)
            company_fields = {
                'language_code': validated_data.pop('company', {}).get('language_code') if validated_data.get('company') else None,
                'work_email': validated_data.pop('company_work_email', None),
                'phone': validated_data.pop('company_phone', None),
                'address': validated_data.pop('company_address', None),
                'china_warehouse_address': validated_data.pop('company_china_warehouse_address', None),
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
    cost_price = serializers.SerializerMethodField()
    automatic_sale_price = serializers.SerializerMethodField()
    applied_markup_pct = serializers.SerializerMethodField()
    applied_markup_source = serializers.SerializerMethodField()

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
            'cost_price',
            'automatic_sale_price',
        )

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        initial_data = getattr(self, 'initial_data', {})
        if (
            'purchase_price' in initial_data
            and not user_has_permission(user, 'pricing.purchase.manage')
        ):
            raise serializers.ValidationError({
                'purchase_price': 'You do not have permission to change the purchase price.'
            })
        if (
            {'sale_price', 'sale_price_mode'}.intersection(initial_data)
            and not user_has_permission(user, 'pricing.sale.catalog.manage')
        ):
            raise serializers.ValidationError({
                'sale_price': 'You do not have permission to change the catalog sale price.'
            })
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
        sale_price_mode = attrs.get(
            'sale_price_mode',
            getattr(self.instance, 'sale_price_mode', Product.SALE_PRICE_MODE_AUTOMATIC),
        )
        submitted_sale_price = attrs.get('sale_price', getattr(self.instance, 'sale_price', Decimal('0.00')))
        previous_mode = getattr(self.instance, 'sale_price_mode', Product.SALE_PRICE_MODE_AUTOMATIC)
        previous_sale_price = getattr(self.instance, 'sale_price', Decimal('0.00'))
        manual_price_changed = (
            sale_price_mode != previous_mode
            or submitted_sale_price != previous_sale_price
        )
        if sale_price_mode == Product.SALE_PRICE_MODE_MANUAL:
            if request and not user_has_permission(request.user, 'pricing.sale.catalog.manage') and manual_price_changed:
                raise serializers.ValidationError({'sale_price': 'Only a company administrator can set a manual sale price.'})
            if submitted_sale_price is None or submitted_sale_price < 0:
                raise serializers.ValidationError({'sale_price': 'Sale price cannot be negative.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not request:
            return data
        user = request.user
        if not user_has_permission(user, 'pricing.purchase.view'):
            data.pop('purchase_price', None)
        if not user_has_permission(user, 'pricing.cost.view'):
            data.pop('cost_price', None)
        if not user_has_permission(user, 'pricing.sale.view'):
            for field_name in ('sale_price', 'automatic_sale_price', 'sale_price_mode'):
                data.pop(field_name, None)
        if not user_has_permission(user, 'company.settings.manage'):
            data.pop('applied_markup_pct', None)
            data.pop('applied_markup_source', None)
        return data

    def _settings(self, product):
        if not hasattr(self, '_settings_cache'):
            try:
                self._settings_cache = product.company.product_settings
            except CompanySettings.DoesNotExist:
                self._settings_cache = CompanySettings.objects.create(
                    company=product.company,
                    **CompanySettings.default_values(product.company.business_country),
                )
        return self._settings_cache

    def get_cost_price(self, product):
        return product.calculate_cost_price(self._settings(product))

    def get_automatic_sale_price(self, product):
        return product.calculate_sale_price(self._settings(product))

    def get_applied_markup_pct(self, product):
        settings = self._settings(product)
        return product.category.margin_pct if product.category and product.category.margin_pct is not None else settings.margin_pct

    def get_applied_markup_source(self, product):
        return 'category' if product.category and product.category.margin_pct is not None else 'company'

    def get_has_history(self, obj):
        return (
            obj.customer_order_items.exists()
            or obj.supplier_order_items.exists()
            or obj.stock_movements.exists()
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if request and not user_has_permission(user, 'pricing.purchase.view'):
            self.fields.pop('purchase_price', None)
        if request and not user_has_permission(user, 'pricing.cost.view'):
            self.fields.pop('cost_price', None)
        if request and not user_has_permission(user, 'pricing.sale.view'):
            for field_name in ('sale_price', 'automatic_sale_price', 'sale_price_mode'):
                self.fields.pop(field_name, None)
        if request and not user_has_permission(user, 'company.settings.manage'):
            self.fields.pop('applied_markup_pct', None)
            self.fields.pop('applied_markup_source', None)
        if request and request.user.is_authenticated:
            company = request.user.company
            self.fields['category_id'].queryset = ProductCategory.objects.filter(company=company)
            self.fields['unit_id'].queryset = Unit.objects.filter(company=company)
            self.fields['supplier_id'].queryset = Counterparty.objects.filter(company=company, is_supplier=True)

    def _calculate_sale_price(self, product):
        if product.sale_price_mode == Product.SALE_PRICE_MODE_MANUAL:
            return product
        if not product.weight_kg or product.weight_kg <= 0:
            product.sale_price = 0
            product.save(update_fields=['sale_price'])
            return product
        settings = self._settings(product)
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
    cost_price = serializers.SerializerMethodField()
    automatic_sale_price = serializers.SerializerMethodField()
    applied_markup_pct = serializers.SerializerMethodField()
    applied_markup_source = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'sku', 'category', 'unit', 'supplier',
            'quantity', 'is_stock_item', 'purchase_price', 'cost_price',
            'sale_price', 'automatic_sale_price', 'sale_price_mode', 'image',
            'applied_markup_pct', 'applied_markup_source',
            'minimum_stock_level', 'average_monthly_consumption',
            'consumption_calculation_mode', 'purchase_batch_size',
            'units_per_package', 'weight_kg', 'length_m', 'width_m', 'height_m',
            'is_archived', 'archived_at', 'archived_by', 'has_history',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if request and not user_has_permission(user, 'pricing.purchase.view'):
            self.fields.pop('purchase_price', None)
        if request and not user_has_permission(user, 'pricing.cost.view'):
            self.fields.pop('cost_price', None)
        if request and not user_has_permission(user, 'pricing.sale.view'):
            for field_name in ('sale_price', 'automatic_sale_price', 'sale_price_mode'):
                self.fields.pop(field_name, None)
        if request and not user_has_permission(user, 'company.settings.manage'):
            self.fields.pop('applied_markup_pct', None)
            self.fields.pop('applied_markup_source', None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not request:
            return data
        user = request.user
        if not user_has_permission(user, 'pricing.purchase.view'):
            data.pop('purchase_price', None)
        if not user_has_permission(user, 'pricing.cost.view'):
            data.pop('cost_price', None)
        if not user_has_permission(user, 'pricing.sale.view'):
            for field_name in ('sale_price', 'automatic_sale_price', 'sale_price_mode'):
                data.pop(field_name, None)
        if not user_has_permission(user, 'company.settings.manage'):
            data.pop('applied_markup_pct', None)
            data.pop('applied_markup_source', None)
        return data

    def get_has_history(self, obj):
        return (
            obj.customer_order_items.exists()
            or obj.supplier_order_items.exists()
            or obj.stock_movements.exists()
        )

    def _settings(self, product):
        if not hasattr(self, '_settings_cache'):
            try:
                self._settings_cache = product.company.product_settings
            except CompanySettings.DoesNotExist:
                self._settings_cache = CompanySettings.objects.create(
                    company=product.company,
                    **CompanySettings.default_values(product.company.business_country),
                )
        return self._settings_cache

    def get_cost_price(self, product):
        return product.calculate_cost_price(self._settings(product))

    def get_automatic_sale_price(self, product):
        return product.calculate_sale_price(self._settings(product))

    def get_applied_markup_pct(self, product):
        settings = self._settings(product)
        return product.category.margin_pct if product.category and product.category.margin_pct is not None else settings.margin_pct

    def get_applied_markup_source(self, product):
        return 'category' if product.category and product.category.margin_pct is not None else 'company'
