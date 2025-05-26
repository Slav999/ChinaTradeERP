from django.contrib import admin
from .models import Product, ProductCategory, Unit, GlobalSettings


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'supplier', 'quantity', 'purchase_price', 'sale_price')
    search_fields = ('name', 'sku')
    list_filter = ('category', 'unit', 'supplier')


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Запретить создание, если уже есть хотя бы одна запись
        return not GlobalSettings.objects.exists()


admin.site.register(ProductCategory)
admin.site.register(Unit)