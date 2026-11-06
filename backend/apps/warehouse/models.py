from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


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
    quantity_defective = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'product'], name='unique_warehouse_stock_per_company_product'),
        ]
        ordering = ('product__name', 'product__sku')

    @property
    def quantity_available(self):
        available = (self.quantity_on_hand or Decimal('0.00')) - (self.quantity_reserved or Decimal('0.00'))
        return max(available, Decimal('0.00'))

    @property
    def quantity_physical(self):
        return (self.quantity_on_hand or Decimal('0.00')) + (self.quantity_defective or Decimal('0.00'))

    def __str__(self):
        return f'{self.product} stock'


class StockMovement(models.Model):
    TYPE_PURCHASE_EXPECTED = 'purchase_expected'
    TYPE_PURCHASE_RECEIVED = 'purchase_received'
    TYPE_CUSTOMER_RESERVED = 'customer_reserved'
    TYPE_CUSTOMER_SHIPPED = 'customer_shipped'
    TYPE_RESERVATION_CANCELLED = 'reservation_cancelled'
    TYPE_ADJUSTMENT = 'adjustment'
    TYPE_DEFECT_RECEIVED = 'defect_received'
    TYPE_DEFECT_RELEASED = 'defect_released'
    TYPE_DEFECT_WRITTEN_OFF = 'defect_written_off'
    TYPE_STOCK_WRITTEN_OFF = 'stock_written_off'

    MOVEMENT_TYPE_CHOICES = (
        (TYPE_PURCHASE_EXPECTED, 'Purchase expected'),
        (TYPE_PURCHASE_RECEIVED, 'Purchase received'),
        (TYPE_CUSTOMER_RESERVED, 'Customer reserved'),
        (TYPE_CUSTOMER_SHIPPED, 'Customer shipped'),
        (TYPE_RESERVATION_CANCELLED, 'Reservation cancelled'),
        (TYPE_ADJUSTMENT, 'Adjustment'),
        (TYPE_DEFECT_RECEIVED, 'Defect received'),
        (TYPE_DEFECT_RELEASED, 'Defect returned to available stock'),
        (TYPE_DEFECT_WRITTEN_OFF, 'Defect written off'),
        (TYPE_STOCK_WRITTEN_OFF, 'Stock written off'),
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


class StockControlSnapshot(models.Model):
    SOURCE_SCHEDULED = 'scheduled'
    SOURCE_MANUAL = 'manual'
    SOURCE_CHOICES = (
        (SOURCE_SCHEDULED, 'Scheduled'),
        (SOURCE_MANUAL, 'Manual'),
    )

    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='stock_control_snapshots',
    )
    schedule_date = models.DateField(db_index=True)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_stock_control_snapshots',
    )
    delivery_lead_days = models.PositiveSmallIntegerField(default=30)
    timezone_name = models.CharField(max_length=64, default='UTC')
    summary = models.JSONField(default=dict)
    items = models.JSONField(default=list)

    class Meta:
        ordering = ('-generated_at', '-id')
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'schedule_date', 'source'],
                name='unique_stock_control_snapshot_per_date_source',
            ),
        ]

    def __str__(self):
        return f'{self.company} stock control {self.schedule_date}'


class StockControlDismissal(models.Model):
    snapshot = models.ForeignKey(
        StockControlSnapshot,
        on_delete=models.CASCADE,
        related_name='dismissals',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_control_dismissals',
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)
    hidden_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['snapshot', 'user'],
                name='unique_stock_control_dismissal_per_user',
            ),
        ]


class StockAlert(models.Model):
    STATUS_CRITICAL = 'critical'

    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='stock_alerts',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stock_alerts',
    )
    status = models.CharField(max_length=24, default=STATUS_CRITICAL)
    available_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    minimum_stock_level = models.DecimalField(max_digits=12, decimal_places=2)
    expected_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    recommended_order_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at', '-id')
        indexes = [
            models.Index(fields=['company', 'resolved_at', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'product', 'status'],
                condition=Q(resolved_at__isnull=True),
                name='unique_active_stock_alert_per_product_status',
            ),
        ]


class StockAlertDismissal(models.Model):
    alert = models.ForeignKey(
        StockAlert,
        on_delete=models.CASCADE,
        related_name='dismissals',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_alert_dismissals',
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)
    hidden_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['alert', 'user'],
                name='unique_stock_alert_dismissal_per_user',
            ),
        ]
