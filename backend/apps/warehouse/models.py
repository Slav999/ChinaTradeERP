from decimal import Decimal

from django.conf import settings
from django.db import models


class WarehouseStock(models.Model):
    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='warehouse_stocks',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='warehouse_stock_records',
    )
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    quantity_reserved = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    quantity_expected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'product'], name='unique_warehouse_stock_per_company_product'),
        ]
        ordering = ('product__name', 'product__sku')

    @property
    def quantity_available(self):
        return (self.quantity_on_hand or Decimal('0.00')) - (self.quantity_reserved or Decimal('0.00'))

    def __str__(self):
        return f'{self.product} stock'


class StockMovement(models.Model):
    TYPE_PURCHASE_EXPECTED = 'purchase_expected'
    TYPE_PURCHASE_RECEIVED = 'purchase_received'
    TYPE_CUSTOMER_RESERVED = 'customer_reserved'
    TYPE_CUSTOMER_SHIPPED = 'customer_shipped'
    TYPE_RESERVATION_CANCELLED = 'reservation_cancelled'
    TYPE_ADJUSTMENT = 'adjustment'

    MOVEMENT_TYPE_CHOICES = (
        (TYPE_PURCHASE_EXPECTED, 'Purchase expected'),
        (TYPE_PURCHASE_RECEIVED, 'Purchase received'),
        (TYPE_CUSTOMER_RESERVED, 'Customer reserved'),
        (TYPE_CUSTOMER_SHIPPED, 'Customer shipped'),
        (TYPE_RESERVATION_CANCELLED, 'Reservation cancelled'),
        (TYPE_ADJUSTMENT, 'Adjustment'),
    )

    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    movement_type = models.CharField(max_length=32, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    source_type = models.CharField(max_length=64, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    source_key = models.CharField(max_length=120, unique=True)
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')
        indexes = [
            models.Index(fields=['company', 'product', 'created_at']),
            models.Index(fields=['source_type', 'source_id']),
        ]

    def __str__(self):
        return f'{self.product} {self.movement_type} {self.quantity}'
