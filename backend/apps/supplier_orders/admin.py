from django.contrib import admin
from .models import (
    SupplierOrder,
    SupplierOrderStatus,
    ShippingAddress,
)


@admin.register(SupplierOrderStatus)
class SupplierOrderStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('default_shipping_address',)


@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'supplier', 'customer', 'status',
        'planned_receipt_date', 'shipment_date', 'china_exit_date',
        'delivery_date', 'amount_cny'
    )
    search_fields = ('status', 'supplier', 'customer')