from django.db import models
from core.models import BaseModel, ChangeLog
from counterparties.models import Counterparty
from products.models import Product
from django.db.models import Max


def get_default_shipping_address():
    """
    Returns the default shipping address from the single ShippingAddress record (if any).
    """
    addr = ShippingAddress.objects.first()
    return addr.default_shipping_address if addr else ''


class CustomerOrderStatus(models.Model):
    """Statuses for customer orders (admin can add/edit)"""
    name = models.CharField("Name", max_length=100, unique=True)
    color = models.CharField("Color (hex)", max_length=7, default="#007bff")

    class Meta:
        verbose_name = "Customer Order Status"
        verbose_name_plural = "Customer Order Statuses"

    def __str__(self):
        return self.name


class ShippingAddress(models.Model):
    """Settings: default shipping address"""
    default_shipping_address = models.TextField(
        "Default Shipping Address", blank=True
    )

    class Meta:
        verbose_name = "Shipping Address Setting"
        verbose_name_plural = "Shipping Address Settings"

    def __str__(self):
        return self.default_shipping_address or '-'


class CustomerOrder(BaseModel):
    """Customer order"""
    order_number = models.CharField(
        "Order Number", max_length=50, unique=True
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
        default=get_default_shipping_address,
        blank=True,
    )
    shipping_code = models.CharField(
        "Shipping Point Code", max_length=100, blank=True
    )
    shipment_date = models.DateField(
        "Shipment Date", blank=True, null=True
    )

    class Meta:
        verbose_name = "Customer Order"
        verbose_name_plural = "Customer Orders"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # apply default shipping address if not provided
        if not self.shipping_address:
            self.shipping_address = get_default_shipping_address()
        # auto-generate order number if not set
        if not self.order_number:
            last_id = (
                CustomerOrder.objects.aggregate(Max('id')).get('id__max') or 0
            )
            self.order_number = str(last_id + 1)
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
    unit = models.CharField(
        "Unit of Measure", max_length=20, blank=True
    )
    comment = models.TextField(
        "Line Comment", blank=True
    )

    class Meta:
        verbose_name = "Customer Order Item"
        verbose_name_plural = "Customer Order Items"

    def __str__(self):
        return f"{self.product.name} — {self.quantity} {self.unit}"


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
