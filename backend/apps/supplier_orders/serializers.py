from rest_framework import serializers
from decimal import Decimal
from django.db.models import Q
from .models import (
    SupplierOrder,
    SupplierOrderStatus,
    SupplierOrderChangeLog,
    SupplierOrderItem,
    ShippingAddress,
    SupplierOrderAttachment
)
from counterparties.models import Counterparty
from products.models import Product
from core.serializers import AuditFieldsMixinSerializer, ChangeLogBaseSerializer
from core.statuses import TranslatableStatusSerializerMixin
from counterparties.serializers import CounterpartySerializer
from products.serializers import ProductSerializer, UnitSerializer
from users.access import user_has_permission


def _supplier_order_items_total_cny(order):
    total = Decimal('0.00')
    for item in order.items.select_related('product'):
        unit_price = item.unit_price_cny
        if unit_price is None:
            unit_price = item.product.purchase_price or Decimal('0.00')
        total += (item.quantity or Decimal('0.00')) * (unit_price or Decimal('0.00'))
    return total.quantize(Decimal('0.01'))


def _file_url(file_field, request, version_source=None):
    if not file_field:
        return None
    try:
        url = file_field.url
    except ValueError:
        return None
    if version_source and getattr(version_source, 'updated_at', None):
        separator = '&' if '?' in url else '?'
        url = f'{url}{separator}v={int(version_source.updated_at.timestamp())}'
    return request.build_absolute_uri(url) if request else url


def _supplier_order_qr_url(order, request):
    return _file_url(
        order.supplier.qr_code_image if order.supplier_id else None,
        request,
        order.supplier if order.supplier_id else None,
    ) or _file_url(
        order.payment_details_qr,
        request,
        order,
    )


class LinkedCustomerOrderSerializer(serializers.ModelSerializer):
    class Meta:
        from customer_orders.models import CustomerOrder
        model = CustomerOrder
        fields = ('id', 'order_number')


class SupplierOrderStatusSerializer(TranslatableStatusSerializerMixin, serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = SupplierOrderStatus
        fields = '__all__'
        read_only_fields = ('company', 'code', 'is_system')
        extra_kwargs = {'name': {'required': False}}

    def validate_name(self, value):
        name = value.strip()
        request = self.context.get('request')
        queryset = SupplierOrderStatus.objects.filter(name__iexact=name)
        if request and request.user.is_authenticated:
            queryset = queryset.filter(company=request.user.company)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Status already exists.')
        return name


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = ('id', 'default_shipping_address')


class SupplierOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    unit = serializers.CharField(source='product.unit.name', read_only=True)

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    order = serializers.PrimaryKeyRelatedField(
        queryset=SupplierOrder.objects.all(),
        write_only=True)

    class Meta:
        model = SupplierOrderItem
        fields = (
            'id', 'order', 'product', 'product_id', 'quantity', 'defective_quantity', 'unit',
            'unit_price_cny', 'comment',
        )
        extra_kwargs = {
            'unit_price_cny': {'required': False, 'allow_null': False},
        }

    def validate_unit_price_cny(self, value):
        if value < 0:
            raise serializers.ValidationError('Purchase price cannot be negative.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        if 'unit_price_cny' in attrs and not user_has_permission(
            getattr(request, 'user', None), 'pricing.purchase.manage'
        ):
            raise serializers.ValidationError({
                'unit_price_cny': 'You do not have permission to change the purchase price.'
            })
        quantity = attrs.get('quantity', getattr(self.instance, 'quantity', Decimal('0.00')))
        defective = attrs.get(
            'defective_quantity',
            getattr(self.instance, 'defective_quantity', Decimal('0.00')),
        )
        if defective < 0:
            raise serializers.ValidationError({'defective_quantity': 'Defective quantity cannot be negative.'})
        if defective > quantity:
            raise serializers.ValidationError({'defective_quantity': 'Defective quantity cannot exceed quantity.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.purchase.view'):
            data.pop('unit_price_cny', None)
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.purchase.view'):
            self.fields.pop('unit_price_cny', None)
        if request and request.user.is_authenticated:
            company = request.user.company
            self.fields['order'].queryset = SupplierOrder.objects.filter(
                company=company
            )
            self.fields['product_id'].queryset = Product.objects.filter(
                company=company,
                is_archived=False,
            )


class SupplierOrderAttachmentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = SupplierOrderAttachment
        fields = ('id', 'file', 'file_name', 'uploaded_at')

    def get_file_name(self, obj):
        return obj.file.name.rsplit('/', 1)[-1]


class OrderCounterpartySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Counterparty
        fields = ('id', 'name')


class SupplierOrderListSerializer(serializers.ModelSerializer):
    supplier = OrderCounterpartySummarySerializer(read_only=True)
    customer = OrderCounterpartySummarySerializer(read_only=True)
    status = SupplierOrderStatusSerializer(read_only=True)
    payment_details_qr = serializers.ImageField(read_only=True)

    class Meta:
        model = SupplierOrder
        fields = (
            'is_sample', 'trip_name', 'id', 'order_number', 'order_year', 'is_previous_year', 'created_at', 'supplier', 'customer',
            'planned_receipt_date', 'shipment_date', 'delivery_date',
            'amount_cny', 'status', 'payment_details_qr', 'track_number', 'sent_at',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.purchase.view'):
            self.fields.pop('amount_cny', None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.purchase.view'):
            data.pop('amount_cny', None)
        if 'amount_cny' in data and instance.amount_cny is None:
            data['amount_cny'] = str(_supplier_order_items_total_cny(instance))
        qr_url = _supplier_order_qr_url(instance, self.context.get('request'))
        if qr_url:
            data['payment_details_qr'] = qr_url
        return data


class SupplierOrderSerializer(AuditFieldsMixinSerializer, serializers.ModelSerializer):
    order_number = serializers.CharField(read_only=True)
    supplier = CounterpartySerializer(read_only=True)
    status = SupplierOrderStatusSerializer(read_only=True)

    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Counterparty.objects.all(),
        source='supplier', write_only=True
    )
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=SupplierOrderStatus.objects.all(),
        source='status', write_only=True,
        required=False, allow_null=True
    )

    customer = CounterpartySerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Counterparty.objects.all(),
        source='customer', write_only=True,
        required=False, allow_null=True
    )
    customer_order = LinkedCustomerOrderSerializer(read_only=True)

    payment_details_qr = serializers.ImageField(read_only=True)
    items = SupplierOrderItemSerializer(many=True, required=False)
    attachments = SupplierOrderAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierOrder
        fields = (
            'is_sample', 'trip_name', 'id', 'order_number', 'order_year', 'is_previous_year', 'created_at', 'updated_at', 'created_by', 'updated_by',
            'status', 'status_id', 'supplier_id', 'supplier', 'customer_id', 'customer',
            'customer_order',
            'planned_receipt_date', 'shipment_date', 'sent_at', 'china_exit_date', 'delivery_date',
            'shipping_address', 'shipping_code', 'supplier_comment', 'internal_comment',
            'amount_cny', 'track_number', 'logistic_invoice_no', 'production_due_date', 'payment_date',
            'cny_to_local_rate', 'company_currency_code', 'company_currency_symbol',
            'payment_details_qr',
            'items', 'attachments',
        )
        read_only_fields = (
            'cny_to_local_rate', 'company_currency_code', 'company_currency_symbol',
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.purchase.view'):
            data.pop('amount_cny', None)
        if request and not user_has_permission(request.user, 'company.settings.manage'):
            data.pop('cny_to_local_rate', None)
        if 'amount_cny' in data and instance.amount_cny is None:
            data['amount_cny'] = str(_supplier_order_items_total_cny(instance))
        qr_url = _supplier_order_qr_url(instance, self.context.get('request'))
        if qr_url:
            data['payment_details_qr'] = qr_url
        return data

    def validate(self, attrs):
        if self.instance and attrs.get('is_sample', self.instance.is_sample) != self.instance.is_sample:
            raise serializers.ValidationError({'is_sample': 'Order type cannot be changed after creation.'})
        request = self.context.get('request')
        if (
            'amount_cny' in attrs
            and not user_has_permission(getattr(request, 'user', None), 'pricing.purchase.manage')
        ):
            raise serializers.ValidationError({
                'amount_cny': 'You do not have permission to change the purchase amount.'
            })
        supplier = attrs.get('supplier', getattr(self.instance, 'supplier', None))
        customer = attrs.get('customer', getattr(self.instance, 'customer', None))
        status = attrs.get('status', getattr(self.instance, 'status', None))
        company = request.user.company if request and request.user.is_authenticated else None

        if company and supplier and supplier.company_id != company.id:
            raise serializers.ValidationError({'supplier_id': 'Selected supplier is not available for your company.'})
        if company and customer and customer.company_id != company.id:
            raise serializers.ValidationError({'customer_id': 'Selected customer is not available for your company.'})
        if company and status and status.company_id != company.id:
            raise serializers.ValidationError({'status_id': 'Selected status is not available for your company.'})
        if supplier and not supplier.is_supplier:
            raise serializers.ValidationError({'supplier_id': 'Selected counterparty is not marked as a supplier.'})
        if customer and not customer.is_customer:
            raise serializers.ValidationError({'customer_id': 'Selected counterparty is not marked as a customer.'})
        return attrs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if request and not user_has_permission(user, 'pricing.purchase.view'):
            self.fields.pop('amount_cny', None)
        if request and not user_has_permission(user, 'company.settings.manage'):
            self.fields.pop('cny_to_local_rate', None)
        if request and request.user.is_authenticated:
            company = request.user.company
            self.fields['status_id'].queryset = SupplierOrderStatus.objects.filter(company=company)
            self.fields['supplier_id'].queryset = Counterparty.objects.filter(company=company, is_supplier=True)
            self.fields['customer_id'].queryset = Counterparty.objects.filter(company=company, is_customer=True)

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        supplier = validated_data.pop('supplier')
        status = validated_data.pop('status', None)
        customer = validated_data.pop('customer', None)

        order = SupplierOrder(**validated_data)
        order.supplier = supplier
        if status is not None:
            order.status = status
        else:
            order.status = SupplierOrderStatus.objects.filter(company=order.company).order_by('id').first()
        if customer is not None:
            order.customer = customer
        order.save()

        for item_data in items_data:
            SupplierOrderItem.objects.create(order=order, **item_data)

        request = self.context['request']
        user = request.user
        for f in request.FILES.getlist('attachments'):
            att = SupplierOrderAttachment.objects.create(order=order, file=f)
            SupplierOrderChangeLog.objects.create(
                supplier_order=order,
                field_name='attachment',
                old_value='',
                new_value=att.file.name,
                changed_by=user,
            )
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        old_values = {k: getattr(instance, k) for k in validated_data.keys()}

        if 'supplier' in validated_data:
            instance.supplier = validated_data.pop('supplier')
        if 'status' in validated_data:
            instance.status = validated_data.pop('status')
        if 'customer' in validated_data:
            instance.customer = validated_data.pop('customer')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        user = self.context['request'].user
        for field, old in old_values.items():
            new = getattr(instance, field)
            # если не изменилось — пропускаем
            if str(old) == str(new):
                continue

            # если старого значения нет — сохраняем пустую строку
            old_val = '' if old is None or old == '' else str(old)
            # для нового тоже можно аналогично, но, как правило, new всегда есть
            new_val = '' if new is None or new == '' else str(new)

            SupplierOrderChangeLog.objects.create(
                supplier_order=instance,
                field_name=field,
                old_value=old_val,
                new_value=new_val,
                changed_by=user,
            )

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                SupplierOrderItem.objects.create(order=instance, **item_data)

        request = self.context['request']
        user = request.user
        for f in request.FILES.getlist('attachments'):
            att = SupplierOrderAttachment.objects.create(order=instance, file=f)
            SupplierOrderChangeLog.objects.create(
                supplier_order=instance,
                field_name='attachment',
                old_value='',
                new_value=att.file.name,
                changed_by=user,
            )
        return instance


class SupplierOrderChangeLogSerializer(ChangeLogBaseSerializer):
    class Meta(ChangeLogBaseSerializer.Meta):
        model = SupplierOrderChangeLog
        fields = ChangeLogBaseSerializer.Meta.fields
