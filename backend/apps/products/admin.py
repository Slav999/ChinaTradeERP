from django.contrib import admin

from .models import CompanySettings, Product, ProductCategory, Unit


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'supplier', 'quantity', 'purchase_price', 'sale_price')
    search_fields = ('name', 'sku')
    list_filter = ('category', 'unit', 'supplier')


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ('company', 'cny_to_local_rate', 'usd_to_local_rate', 'internal_logistics_pct', 'margin_pct')
    search_fields = ('company__name',)


admin.site.register(ProductCategory)
admin.site.register(Unit)
