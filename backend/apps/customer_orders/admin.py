from django.contrib import admin
from .models import (
    CustomerOrder,
    CustomerOrderStatus,
    ShippingAddress,
)


@admin.register(CustomerOrderStatus)
class CustomerOrderStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('default_shipping_address',)


@admin.register(CustomerOrder)
class CustomerOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'customer', 'status',
    )
    search_fields = ('status', 'supplier', 'customer')