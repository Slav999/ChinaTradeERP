from django.db import models
from core.models import BaseModel, ChangeLog, AnnualOrderModel
from counterparties.models import Counterparty
from products.models import Product
from decimal import Decimal
from users.models import Company


def get_default_shipping_address(company=None):
    """
    Returns the default shipping address from the single ShippingAddress record (if any).
    """
    if company:
        addr = ShippingAddress.objects.filter(company=company).first()
    else:
        addr = ShippingAddress.objects.first()
    return addr.default_shipping_address if addr else ''


class CustomerOrderStatus(models.Model):
    """Statuses for customer orders (admin can add/edit)"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='customer_order_statuses',
    )
    name = models.CharField("Name", max_length=100)
    code = models.CharField(max_length=50, null=True, blank=True)
    translations = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
    color = models.CharField("Color (hex)", max_length=7, default="#007bff")

    class Meta:
        verbose_name = "Customer Order Status"
        verbose_name_plural = "Customer Order Statuses"
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_customer_order_status_per_company'),
            models.UniqueConstraint(fields=['company', 'code'], name='unique_customer_order_status_code_per_company'),
        ]

    def display_name(self, language=None):
        from core.statuses import status_display_name
        return status_display_name(self, language)

    def __str__(self):
        return self.name


class ShippingAddress(models.Model):
    """Settings: default shipping address"""
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='customer_shipping_address',
    )
    default_shipping_address = models.TextField(
        "Default Shipping Address", blank=True
    )

    class Meta:
        verbose_name = "Shipping Address Setting"
        verbose_name_plural = "Shipping Address Settings"

    def __str__(self):
        return self.default_shipping_address or '-'


class CustomerOrder(AnnualOrderModel):
    """Customer order"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='customer_orders',
    )
    order_number = models.CharField(
        "Order Number", max_length=50
    )
    created_at = models.DateTimeField(
        "Creation Date", auto_now_add=True
    )
    status = models.ForeignKey(
        CustomerOrderStatus,
        verbose_name="Status",
        on_delete=models.PROTECT,
        related_name="customer_orders",
    )
    customer = models.ForeignKey(
        Counterparty,
        verbose_name="Customer",
        on_delete=models.PROTECT,
        related_name="customer_orders",
        blank=True,
        null=True,
    )
    planned_receipt_date = models.DateField(
        "Planned Receipt Date", blank=True, null=True
    )
    shipping_address = models.TextField(
        "Shipping Address",
        blank=True,
    )
    shipping_code = models.CharField(
        "Shipping Point Code", max_length=100, blank=True
    )
    shipment_date = models.DateField(
        "Shipment Date", blank=True, null=True
    )
    sent_at = models.DateTimeField(
        "Sent At", blank=True, null=True
    )
    discount_pct = models.DecimalField(
        "Order Discount (%)",
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
    )
    customer_comment = models.TextField(
        "Comment for Customer",
        blank=True,
    )
    internal_comment = models.TextField(
        "Internal Comment",
        blank=True,
    )

    class Meta:
        verbose_name = "Customer Order"
        verbose_name_plural = "Customer Orders"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['company', 'order_year', 'order_number'], name='unique_customer_order_number_per_year'),
        ]

    def save(self, *args, **kwargs):
        if not self.company_id and self.customer_id:
            self.company = self.customer.company
        # auto-generate order number if not set
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.order_number} — {self.customer.name}"


class CustomerOrderItem(models.Model):
    """Items/lines in a customer order"""
    order = models.ForeignKey(
        CustomerOrder,
        verbose_name="Order",
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        verbose_name="Product",
        on_delete=models.PROTECT,
        related_name='customer_order_items'
    )
    quantity = models.DecimalField(
        "Quantity",
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    unit_sale_price = models.DecimalField(
        "Sale price per unit at order creation",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )
    unit = models.CharField(
        "Unit of Measure", max_length=20, blank=True
    )
    comment = models.TextField(
        "Line Comment", blank=True
    )
    discount_pct = models.DecimalField(
        "Line Discount (%)",
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
    )

    class Meta:
        verbose_name = "Customer Order Item"
        verbose_name_plural = "Customer Order Items"

    def __str__(self):
        return f"{self.product.name} — {self.quantity} {self.unit}"

    def save(self, *args, **kwargs):
        if self._state.adding and self.product_id and self.unit_sale_price is None:
            self.unit_sale_price = self.product.sale_price or Decimal('0.00')
        super().save(*args, **kwargs)


class CustomerOrderAttachment(models.Model):
    """Files attached to a customer order"""
    order = models.ForeignKey(
        CustomerOrder,
        related_name='attachments',
        on_delete=models.CASCADE,
        verbose_name='Order'
    )
    file = models.FileField(
        upload_to='customer_order_attachments/',
        verbose_name='Attachment File'
    )
    uploaded_at = models.DateTimeField(
        'Uploaded At', auto_now_add=True
    )

    class Meta:
        verbose_name = 'Customer Order Attachment'
        verbose_name_plural = 'Customer Order Attachments'

    def __str__(self):
        return f"Order #{self.order.order_number} – {self.file.name}"


class CustomerOrderChangeLog(ChangeLog):
    """Change history for customer orders"""
    customer_order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name='history'
    )

    class Meta:
        verbose_name = "Customer Order Change Log"
        verbose_name_plural = "Customer Order Change Logs"

    def __str__(self):
        return f"{self.customer_order.order_number}: {self.field_name} changed"
