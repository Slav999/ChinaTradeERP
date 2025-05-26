from rest_framework import serializers
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
from counterparties.serializers import CounterpartySerializer
from products.serializers import ProductSerializer, UnitSerializer


class SupplierOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierOrderStatus
        fields = '__all__'


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
        fields = ('id', 'order', 'product', 'product_id', 'quantity', 'unit', 'comment')


class SupplierOrderAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierOrderAttachment
        fields = ('id', 'file', 'uploaded_at')


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

    payment_details_qr = serializers.ImageField(read_only=True)
    items = SupplierOrderItemSerializer(many=True, required=False)
    attachments = SupplierOrderAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierOrder
        fields = (
            'id', 'order_number', 'created_at', 'updated_at', 'created_by', 'updated_by',
            'status', 'status_id', 'supplier_id', 'supplier', 'customer_id', 'customer',
            'planned_receipt_date', 'shipment_date', 'china_exit_date', 'delivery_date',
            'shipping_address', 'shipping_code', 'supplier_comment',
            'amount_cny', 'track_number', 'logistic_invoice_no', 'production_due_date', 'payment_date',
            'payment_details_qr',
            'items', 'attachments',
        )

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        supplier = validated_data.pop('supplier')
        status = validated_data.pop('status', None)
        customer = validated_data.pop('customer', None)

        order = SupplierOrder(**validated_data)
        order.supplier = supplier
        if status is not None:
            order.status = status
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