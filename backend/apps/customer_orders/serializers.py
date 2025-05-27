from rest_framework import serializers
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
from counterparties.serializers import CounterpartySerializer
from products.serializers import ProductSerializer, UnitSerializer


class CustomerOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerOrderStatus
        fields = '__all__'


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = ('id', 'default_shipping_address')


class CustomerOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    unit = serializers.CharField(source='product.unit.name', read_only=True)

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product', write_only=True
    )
    order = serializers.PrimaryKeyRelatedField(
        queryset=CustomerOrder.objects.all(), write_only=True
    )

    class Meta:
        model = CustomerOrderItem
        fields = ('id', 'order', 'product', 'product_id', 'quantity', 'unit', 'comment')


class CustomerOrderAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerOrderAttachment
        fields = ('id', 'file', 'uploaded_at')


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
        required=False, allow_null=True
    )
    items = CustomerOrderItemSerializer(many=True, required=False)
    attachments = CustomerOrderAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = CustomerOrder
        fields = (
            'id', 'order_number', 'created_at', 'updated_at', 'created_by', 'updated_by',
            'status', 'status_id', 'customer', 'customer_id',
            'planned_receipt_date', 'shipment_date',
            'shipping_address', 'shipping_code',
            'items', 'attachments',
        )

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        status = validated_data.pop('status', None)
        customer = validated_data.pop('customer', None)

        order = CustomerOrder(**validated_data)
        if status is not None:
            order.status = status
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
