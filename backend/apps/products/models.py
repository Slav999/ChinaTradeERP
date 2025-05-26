from django.db import models
from counterparties.models import Counterparty
from core.models import BaseModel, ChangeLog
from decimal import Decimal


class ProductCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class GlobalSettings(models.Model):
    cny_to_local_rate = models.DecimalField(
        "CNY → Local Rate", max_digits=12, decimal_places=6,
        help_text="Local currency units per 1 CNY"
    )
    usd_to_local_rate = models.DecimalField(
        "USD → Local Rate", max_digits=12, decimal_places=6,
        help_text="Local currency units per 1 USD"
    )
    logistics_cost_per_kg_usd = models.DecimalField(
        "Logistics Cost (USD/kg)", max_digits=10, decimal_places=2,
        help_text="Cost of logistics per kilogram in USD"
    )
    retail_tax_pct = models.DecimalField(
        "Retail Tax (%)", max_digits=5, decimal_places=4,
        default=Decimal('0.08'),
        help_text="Enter 0.08 for 8%"
    )
    acquiring_pct = models.DecimalField(
        "Acquiring Fee (%)", max_digits=5, decimal_places=4,
        default=Decimal('0.01'),
        help_text="Enter 0.01 for 1%"
    )
    packaging_pct = models.DecimalField(
        "Packaging Fee (%)", max_digits=5, decimal_places=4,
        default=Decimal('0.01'),
        help_text="Enter 0.01 for 1%"
    )
    margin_pct = models.DecimalField(
        "Margin (%)", max_digits=5, decimal_places=4,
        default=Decimal('0.50'),
        help_text="Enter 0.10 for 10%"
    )
    discount_pct = models.DecimalField(
        "Discount (%)", max_digits=5, decimal_places=4,
        default=Decimal('0.10'),
        help_text="Enter 0.10 for 10%"
    )

    def __str__(self):
        return "Global Settings"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalculate sale_price for all products after settings change
        from .models import Product
        settings = GlobalSettings.objects.first()
        for product in Product.objects.all():
            product.sale_price = product.calculate_sale_price(settings)
            product.save(update_fields=['sale_price'])


class Product(BaseModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sale_price = models.DecimalField("Sale Price (Local)", max_digits=10, decimal_places=2, default=Decimal('0.00'))
    quantity = models.IntegerField(default=0)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    supplier = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name='products'
    )
    units_per_package = models.PositiveIntegerField(
        "Units per package", default=1,
        help_text="Number of items in one package/box"
    )
    weight_kg = models.DecimalField(
        "Weight per unit (kg)", max_digits=8, decimal_places=3,
        null=True, blank=True
    )
    length_m = models.DecimalField(
        "Box length (m)", max_digits=8, decimal_places=3,
        null=True, blank=True
    )
    width_m = models.DecimalField(
        "Box width (m)", max_digits=8, decimal_places=3,
        null=True, blank=True
    )
    height_m = models.DecimalField(
        "Box height (m)", max_digits=8, decimal_places=3,
        null=True, blank=True
    )

    def calculate_sale_price(self, settings: GlobalSettings) -> Decimal:
        """
        1) Стоимость единицы в локальной валюте
        2) Стоимость коробки
        3) Логистика
        4) Итоговая себестоимость коробки
        5) Себестоимость за единицу
        6) Маржа, скидка
        7) Сборы (налог, эквайринг, упаковка)
        8) Итоговая цена за единицу
        """
        # 1) Local unit cost
        unit_cost_local = (self.purchase_price or Decimal('0.00')) * settings.cny_to_local_rate

        # 2) Package cost in local
        package_cost_local = unit_cost_local * self.units_per_package

        # 3) Box weight
        box_weight = (self.weight_kg or Decimal('0.00')) * self.units_per_package

        # 4) Logistics
        logistics_usd = box_weight * settings.logistics_cost_per_kg_usd
        logistics_local = logistics_usd * settings.usd_to_local_rate

        # 5) Total package cost
        total_package_cost = package_cost_local + logistics_local

        # 5a) Cost per single unit
        cost_per_unit = total_package_cost / self.units_per_package

        # 6) Margin & discount
        with_margin = cost_per_unit * (1 + settings.margin_pct)
        after_discount = with_margin * (1 - settings.discount_pct)

        # 7) Fee sum
        fee_sum = (
            after_discount * settings.retail_tax_pct +
            after_discount * settings.acquiring_pct +
            after_discount * settings.packaging_pct
        )

        # 8) Final per-unit price
        return (after_discount + fee_sum).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductChangeLog(ChangeLog):
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='history'
    )

    def __str__(self):
        return f"{self.product.name}: {self.field_name} changed"



