from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from counterparties.models import Counterparty
from core.models import BaseModel, ChangeLog
from decimal import Decimal, ROUND_HALF_UP
from datetime import time
import pytz
from users.company_defaults import company_defaults_for_country


DEFAULT_COMPANY_SETTINGS = {
    'cny_to_local_rate': Decimal('1.00'),
    'usd_to_local_rate': Decimal('1.00'),
    'logistics_cost_per_kg_usd': Decimal('0.00'),
    'internal_logistics_pct': Decimal('0.00'),
    'retail_tax_pct': Decimal('0.08'),
    'acquiring_pct': Decimal('0.01'),
    'packaging_pct': Decimal('0.01'),
    'margin_pct': Decimal('0.50'),
}


class ProductCategory(models.Model):
    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='product_categories',
    )
    name = models.CharField(max_length=100)
    margin_pct = models.DecimalField(
        "Markup (%)",
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Leave empty to use the company markup.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_product_category_per_company'),
        ]

    def __str__(self):
        return self.name


class Unit(models.Model):
    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='product_units',
    )
    name = models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_unit_per_company'),
        ]

    def __str__(self):
        return self.name


class CompanySettings(models.Model):
    STOCK_CONSUMPTION_HISTORY_CHOICES = (
        (30, '30 days'),
        (90, '90 days'),
        (180, '180 days'),
    )
    company = models.OneToOneField(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='product_settings',
    )
    cny_to_local_rate = models.DecimalField(
        "CNY → Local Rate", max_digits=12, decimal_places=2,
        default=DEFAULT_COMPANY_SETTINGS['cny_to_local_rate'],
        help_text="Local currency units per 1 CNY"
    )
    usd_to_local_rate = models.DecimalField(
        "USD → Local Rate", max_digits=12, decimal_places=2,
        default=DEFAULT_COMPANY_SETTINGS['usd_to_local_rate'],
        help_text="Local currency units per 1 USD"
    )
    logistics_cost_per_kg_usd = models.DecimalField(
        "Logistics Cost (USD/kg)", max_digits=10, decimal_places=2,
        default=DEFAULT_COMPANY_SETTINGS['logistics_cost_per_kg_usd'],
        help_text="Cost of logistics per kilogram in USD"
    )
    internal_logistics_pct = models.DecimalField(
        "Internal Logistics (%)", max_digits=5, decimal_places=4,
        default=DEFAULT_COMPANY_SETTINGS['internal_logistics_pct'],
        help_text="Enter 0.01 for 1%"
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
        "Markup (%)", max_digits=5, decimal_places=4,
        default=Decimal('0.50'),
        help_text="Enter 0.10 for a 10% markup"
    )
    rates_updated_at = models.DateTimeField(null=True, blank=True)
    settings_confirmed_at = models.DateTimeField(null=True, blank=True)
    stock_delivery_lead_days = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text='Average number of days between ordering and warehouse receipt.',
    )
    stock_timezone = models.CharField(max_length=64, default='Asia/Almaty')
    stock_weekly_control_enabled = models.BooleanField(default=True)
    stock_notification_weekday = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text='Monday is 0 and Sunday is 6.',
    )
    stock_notification_time = models.TimeField(default=time(10, 0))
    stock_consumption_history_days = models.PositiveSmallIntegerField(
        choices=STOCK_CONSUMPTION_HISTORY_CHOICES,
        default=90,
        help_text='Number of calendar days used for automatic stock consumption.',
    )

    def __str__(self):
        return f"{self.company.name} Settings"

    @classmethod
    def default_values(cls, country_code=None):
        values = DEFAULT_COMPANY_SETTINGS.copy()
        if country_code:
            values['retail_tax_pct'] = company_defaults_for_country(country_code)['retail_tax_pct']
            country = str(country_code).upper()
            primary_timezones = {
                'KZ': 'Asia/Almaty',
                'RU': 'Europe/Moscow',
                'CN': 'Asia/Shanghai',
                'US': 'America/New_York',
            }
            values['stock_timezone'] = (
                primary_timezones.get(country)
                or next(iter(pytz.country_timezones.get(country, [])), 'UTC')
            )
        return values

    def confirm_settings(self):
        self.settings_confirmed_at = timezone.now()
        self.save(update_fields=['settings_confirmed_at'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for product in Product.objects.filter(
            company=self.company,
            sale_price_mode=Product.SALE_PRICE_MODE_AUTOMATIC,
        ).select_related('category'):
            product.sale_price = product.calculate_sale_price(self)
            product.save(update_fields=['sale_price'])


class Product(BaseModel):
    SALE_PRICE_MODE_AUTOMATIC = 'automatic'
    SALE_PRICE_MODE_MANUAL = 'manual'
    SALE_PRICE_MODE_CHOICES = (
        (SALE_PRICE_MODE_AUTOMATIC, 'Automatic'),
        (SALE_PRICE_MODE_MANUAL, 'Manual'),
    )
    CONSUMPTION_MODE_MANUAL = 'manual'
    CONSUMPTION_MODE_AUTOMATIC = 'automatic'
    CONSUMPTION_MODE_CHOICES = (
        (CONSUMPTION_MODE_MANUAL, 'Manual'),
        (CONSUMPTION_MODE_AUTOMATIC, 'Automatic'),
    )
    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='products',
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
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
    sale_price_mode = models.CharField(
        max_length=16,
        choices=SALE_PRICE_MODE_CHOICES,
        default=SALE_PRICE_MODE_AUTOMATIC,
    )
    quantity = models.IntegerField(default=0)
    is_stock_item = models.BooleanField(default=False)
    minimum_stock_level = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    average_monthly_consumption = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    consumption_calculation_mode = models.CharField(
        max_length=16,
        choices=CONSUMPTION_MODE_CHOICES,
        default=CONSUMPTION_MODE_AUTOMATIC,
    )
    purchase_batch_size = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Quantity in one purchasing batch, roll, box, or other supplier lot.',
    )
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
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_products'
    )

    def calculate_cost_price(self, settings: CompanySettings) -> Decimal:
        """Current full cost of one unit in the company's local currency."""
        if not self.weight_kg or self.weight_kg <= 0:
            return Decimal('0.00')
        purchase_cost = (self.purchase_price or Decimal('0.00')) * settings.cny_to_local_rate
        international_logistics = (
            (self.weight_kg or Decimal('0.00'))
            * settings.logistics_cost_per_kg_usd
            * settings.usd_to_local_rate
        )
        landed_cost = purchase_cost + international_logistics
        internal_logistics = landed_cost * settings.internal_logistics_pct
        before_packaging = landed_cost + internal_logistics
        packaging = before_packaging * settings.packaging_pct
        return (before_packaging + packaging).quantize(Decimal('0.01'))

    def calculate_sale_price(self, settings: CompanySettings) -> Decimal:
        """Automatic price preserving the configured markup after sales deductions."""
        full_cost_per_unit = self.calculate_cost_price(settings)
        if full_cost_per_unit <= 0:
            return Decimal('0.00')
        markup_pct = (
            self.category.margin_pct
            if self.category and self.category.margin_pct is not None
            else settings.margin_pct
        )
        target_after_deductions = full_cost_per_unit * (Decimal('1.00') + markup_pct)
        deduction_rate = settings.retail_tax_pct + settings.acquiring_pct
        if deduction_rate >= Decimal('1.00'):
            raise ValueError('Retail tax and acquiring fee must total less than 100%.')
        price = target_after_deductions / (Decimal('1.00') - deduction_rate)
        currency_code = (settings.company.base_currency_code or '').upper()
        quantum = Decimal('1') if currency_code in {'KZT', 'RUB'} else Decimal('0.01')
        return price.quantize(quantum, rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        if not self.company_id and self.supplier_id:
            self.company = self.supplier.company
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'sku'], name='unique_product_sku_per_company'),
        ]

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



