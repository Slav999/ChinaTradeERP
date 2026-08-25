from django.contrib import admin

from .models import StockMovement, WarehouseStock


@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'company', 'quantity_on_hand', 'quantity_reserved', 'quantity_expected', 'updated_at')
    list_filter = ('company',)
    search_fields = ('product__name', 'product__sku')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'company', 'movement_type', 'quantity', 'source_type', 'source_id', 'created_at')
    list_filter = ('company', 'movement_type', 'source_type')
    search_fields = ('product__name', 'product__sku', 'source_key')
