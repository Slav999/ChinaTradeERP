from rest_framework import serializers
from decimal import Decimal
from .models import (
    CustomerOrder,
    CustomerOrderStatus,
    CustomerOrderChangeLog,
    CustomerOrderItem,
    ShippingAddress,
    CustomerOrderAttachment
)
from counterparties.models import Counterparty
from products.models import Product
from core.serializers import AuditFieldsMixinSerializer, ChangeLogBaseSerializer
from core.statuses import TranslatableStatusSerializerMixin
from counterparties.serializers import CounterpartySerializer
from products.serializers import ProductSerializer, UnitSerializer
from users.access import user_has_permission


class CustomerOrderStatusSerializer(TranslatableStatusSerializerMixin, serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerOrderStatus
        fields = '__all__'
        read_only_fields = ('company', 'code', 'is_system')
        extra_kwargs = {'name': {'required': False}}

    def validate_name(self, value):
        name = value.strip()
        request = self.context.get('request')
        queryset = CustomerOrderStatus.objects.filter(name__iexact=name)
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


class CustomerOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    unit = serializers.CharField(source='product.unit.name', read_only=True)
    line_total_before_discount = serializers.SerializerMethodField()
    line_total_after_discount = serializers.SerializerMethodField()

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product', write_only=True
    )
    order = serializers.PrimaryKeyRelatedField(
        queryset=CustomerOrder.objects.all(), write_only=True
    )

    class Meta:
        model = CustomerOrderItem
        fields = (
            'id', 'order', 'product', 'product_id', 'quantity', 'unit', 'comment',
            'discount_pct', 'unit_sale_price', 'line_total_before_discount',
            'line_total_after_discount',
        )
        extra_kwargs = {
            'unit_sale_price': {'required': False, 'allow_null': False},
        }

    def get_line_total_before_discount(self, obj):
        unit_price = obj.unit_sale_price
        if unit_price is None:
            unit_price = obj.product.sale_price or Decimal('0.00')
        quantity = obj.quantity or Decimal('0.00')
        return (unit_price * quantity).quantize(Decimal('0.01'))

    def get_line_total_after_discount(self, obj):
        unit_price = obj.unit_sale_price
        if unit_price is None:
            unit_price = obj.product.sale_price or Decimal('0.00')
        quantity = obj.quantity or Decimal('0.00')
        discount_pct = obj.discount_pct or Decimal('0.0000')
        return (unit_price * quantity * (Decimal('1.0000') - discount_pct)).quantize(Decimal('0.01'))

    def validate_discount_pct(self, value):
        if value < 0 or value > 1:
            raise serializers.ValidationError('Discount must be between 0 and 100%.')
        return value

    def validate_unit_sale_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Sale price cannot be negative.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if (
            {'unit_sale_price', 'discount_pct'}.intersection(attrs)
            and not user_has_permission(getattr(request, 'user', None), 'pricing.sale.order.manage')
        ):
            raise serializers.ValidationError({
                'unit_sale_price': 'You do not have permission to change sale prices or discounts.'
            })
        order = attrs.get('order', getattr(self.instance, 'order', None))
        discount_pct = attrs.get('discount_pct', getattr(self.instance, 'discount_pct', Decimal('0.0000')))
        if order and order.pk:
            order.refresh_from_db(fields=['discount_pct'])
        if order and order.discount_pct and order.discount_pct > 0 and discount_pct and discount_pct > 0:
            raise serializers.ValidationError({
                'discount_pct': 'Remove the order discount before setting a product discount.'
            })
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.sale.view'):
            for field_name in (
                'discount_pct', 'unit_sale_price', 'line_total_before_discount',
                'line_total_after_discount',
            ):
                data.pop(field_name, None)
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.sale.view'):
            for field_name in (
                'discount_pct', 'unit_sale_price', 'line_total_before_discount',
                'line_total_after_discount',
            ):
                self.fields.pop(field_name, None)
        if request and request.user.is_authenticated:
            company = request.user.company
            self.fields['order'].queryset = CustomerOrder.objects.filter(
                company=company
            )
            self.fields['product_id'].queryset = Product.objects.filter(
                company=company,
                is_archived=False,
            )


class CustomerOrderAttachmentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerOrderAttachment
        fields = ('id', 'file', 'file_name', 'uploaded_at')

    def get_file_name(self, obj):
        return obj.file.name.rsplit('/', 1)[-1]


class OrderCounterpartySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Counterparty
        fields = ('id', 'name')


class CustomerOrderListSerializer(serializers.ModelSerializer):
    customer = OrderCounterpartySummarySerializer(read_only=True)
    status = CustomerOrderStatusSerializer(read_only=True)

    class Meta:
        model = CustomerOrder
        fields = (
            'id', 'order_number', 'order_year', 'is_previous_year', 'created_at', 'customer',
            'planned_receipt_date', 'shipment_date',
            'shipping_code', 'status', 'sent_at',
        )


class CustomerOrderSerializer(AuditFieldsMixinSerializer, serializers.ModelSerializer):
    order_number = serializers.CharField(read_only=True)
    status = CustomerOrderStatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomerOrderStatus.objects.all(),
        source='status', write_only=True,
        required=False, allow_null=True
    )
    customer = CounterpartySerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Counterparty.objects.all(),
        source='customer', write_only=True,
        required=True, allow_null=False
    )
    items = CustomerOrderItemSerializer(many=True, required=False)
    attachments = CustomerOrderAttachmentSerializer(many=True, read_only=True)
    subtotal_before_order_discount = serializers.SerializerMethodField()
    order_discount_amount = serializers.SerializerMethodField()
    total_after_discount = serializers.SerializerMethodField()

    class Meta:
        model = CustomerOrder
        fields = (
            'id', 'order_number', 'order_year', 'is_previous_year', 'created_at', 'updated_at', 'created_by', 'updated_by',
            'status', 'status_id', 'customer', 'customer_id',
            'planned_receipt_date', 'shipment_date', 'sent_at',
            'shipping_address', 'shipping_code', 'discount_pct',
            'customer_comment', 'internal_comment',
            'items', 'attachments',
            'subtotal_before_order_discount', 'order_discount_amount', 'total_after_discount',
        )

    def _items_subtotal(self, obj):
        total = Decimal('0.00')
        items = obj.items.select_related('product').all()
        for item in items:
            unit_price = item.unit_sale_price
            if unit_price is None:
                unit_price = item.product.sale_price or Decimal('0.00')
            quantity = item.quantity or Decimal('0.00')
            line_discount = item.discount_pct or Decimal('0.0000')
            total += unit_price * quantity * (Decimal('1.0000') - line_discount)
        return total.quantize(Decimal('0.01'))

    def get_subtotal_before_order_discount(self, obj):
        return self._items_subtotal(obj)

    def get_order_discount_amount(self, obj):
        subtotal = self._items_subtotal(obj)
        discount_pct = obj.discount_pct or Decimal('0.0000')
        return (subtotal * discount_pct).quantize(Decimal('0.01'))

    def get_total_after_discount(self, obj):
        subtotal = self._items_subtotal(obj)
        discount_pct = obj.discount_pct or Decimal('0.0000')
        return (subtotal * (Decimal('1.0000') - discount_pct)).quantize(Decimal('0.01'))

    def validate(self, attrs):
        request = self.context.get('request')
        if (
            'discount_pct' in getattr(self, 'initial_data', {})
            and not user_has_permission(getattr(request, 'user', None), 'pricing.sale.order.manage')
        ):
            raise serializers.ValidationError({
                'discount_pct': 'You do not have permission to change sale prices or discounts.'
            })
        customer = attrs.get('customer', getattr(self.instance, 'customer', None))
        status = attrs.get('status', getattr(self.instance, 'status', None))
        discount_pct = attrs.get('discount_pct', getattr(self.instance, 'discount_pct', Decimal('0.0000')))
        if request and request.user.is_authenticated and customer and customer.company_id != request.user.company_id:
            raise serializers.ValidationError({'customer_id': 'Selected customer is not available for your company.'})
        if request and request.user.is_authenticated and status and status.company_id != request.user.company_id:
            raise serializers.ValidationError({'status_id': 'Selected status is not available for your company.'})
        if not customer:
            raise serializers.ValidationError({'customer_id': 'Select a customer before saving the order.'})
        if customer and not customer.is_customer:
            raise serializers.ValidationError({'customer_id': 'Selected counterparty is not marked as a customer.'})
        if discount_pct and discount_pct > 0 and self.instance:
            has_line_discount = self.instance.items.filter(discount_pct__gt=0).exists()
            if has_line_discount:
                raise serializers.ValidationError({
                    'discount_pct': 'Remove product discounts before setting an order discount.'
                })
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.sale.view'):
            for field_name in (
                'discount_pct', 'subtotal_before_order_discount',
                'order_discount_amount', 'total_after_discount',
            ):
                data.pop(field_name, None)
        return data

    def validate_discount_pct(self, value):
        if value < 0 or value > 1:
            raise serializers.ValidationError('Discount must be between 0 and 100%.')
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not user_has_permission(request.user, 'pricing.sale.view'):
            for field_name in (
                'discount_pct', 'subtotal_before_order_discount',
                'order_discount_amount', 'total_after_discount',
            ):
                self.fields.pop(field_name, None)
        if request and request.user.is_authenticated:
            company = request.user.company
            self.fields['status_id'].queryset = CustomerOrderStatus.objects.filter(company=company)
            self.fields['customer_id'].queryset = Counterparty.objects.filter(company=company, is_customer=True)

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        status = validated_data.pop('status', None)
        customer = validated_data.pop('customer', None)

        order = CustomerOrder(**validated_data)
        if status is not None:
            order.status = status
        else:
            order.status = CustomerOrderStatus.objects.filter(company=order.company).order_by('id').first()
        if customer is not None:
            order.customer = customer
        order.save()

        for item_data in items_data:
            CustomerOrderItem.objects.create(order=order, **item_data)

        request = self.context['request']
        user = request.user
        for f in request.FILES.getlist('attachments'):
            att = CustomerOrderAttachment.objects.create(order=order, file=f)
            CustomerOrderChangeLog.objects.create(
                customer_order=order,
                field_name='attachment',
                old_value='',
                new_value=att.file.name,
                changed_by=user,
            )
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        old_values = {k: getattr(instance, k) for k in validated_data.keys()}

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
            if str(old) == str(new):
                continue

            old_val = '' if old is None or old == '' else str(old)
            new_val = '' if new is None or new == '' else str(new)

            CustomerOrderChangeLog.objects.create(
                customer_order=instance,
                field_name=field,
                old_value=old_val,
                new_value=new_val,
                changed_by=user,
            )

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                CustomerOrderItem.objects.create(order=instance, **item_data)

        request = self.context['request']
        user = request.user
        for f in request.FILES.getlist('attachments'):
            att = CustomerOrderAttachment.objects.create(order=instance, file=f)
            CustomerOrderChangeLog.objects.create(
                customer_order=instance,
                field_name='attachment',
                old_value='',
                new_value=att.file.name,
                changed_by=user,
            )
        return instance


class CustomerOrderChangeLogSerializer(ChangeLogBaseSerializer):
    class Meta(ChangeLogBaseSerializer.Meta):
        model = CustomerOrderChangeLog
        fields = ChangeLogBaseSerializer.Meta.fields
