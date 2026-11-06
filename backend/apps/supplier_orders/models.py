from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from core.models import BaseModel, ChangeLog, AnnualOrderModel
from counterparties.models import Counterparty
from products.models import Product
from users.models import Company
from decimal import Decimal


def get_default_shipping_address(company=None):
    """
    Возвращает дефолтный адрес из единственной записи ShippingAddress (если есть).
    """
    return company.china_warehouse_address if company and company.china_warehouse_address else ''


class SupplierOrderStatus(models.Model):
    """Статусы заказа поставщику (админ может добавлять/редактировать)"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='supplier_order_statuses',
    )
    name = models.CharField("Name", max_length=100)
    code = models.CharField(max_length=50, null=True, blank=True)
    translations = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
    color = models.CharField("Цвет (hex)", max_length=7, default="#007bff")

    class Meta:
        verbose_name = "Статус заказа поставщику"
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_supplier_order_status_per_company'),
            models.UniqueConstraint(fields=['company', 'code'], name='unique_supplier_order_status_code_per_company'),
        ]
        verbose_name_plural = "Статусы заказа поставщику"

    def __str__(self):
        return self.name

    def display_name(self, language=None):
        from core.statuses import status_display_name
        return status_display_name(self, language)



class ShippingAddress(models.Model):
    """Default supplier shipping address settings."""
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='supplier_shipping_address',
    )
    default_shipping_address = models.TextField(
        "Default Shipping Address", blank=True
    )

    def __str__(self):
        return self.default_shipping_address or '-'


class SupplierOrder(AnnualOrderModel):
    """Supplier order"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='supplier_orders',
    )
    is_sample = models.BooleanField('Sample order', default=False, db_index=True)
    trip_name = models.CharField('Trip / exhibition / meeting', max_length=255, blank=True, default='')
    has_defects = models.BooleanField('Has defects', default=False)
    order_number = models.CharField(
        "Order Number", max_length=50
    )
    created_at = models.DateTimeField(
        "Дата создания", auto_now_add=True
    )
    status = models.ForeignKey(
        SupplierOrderStatus,
        verbose_name="Статус",
        on_delete=models.PROTECT,
        related_name="supplier_orders",
    )
    supplier = models.ForeignKey(
        Counterparty,
        verbose_name="Поставщик",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    customer = models.ForeignKey(
        Counterparty,
        verbose_name="Покупатель",
        on_delete=models.PROTECT,
        related_name="sales_orders",
        blank=True,
        null=True,
    )
    customer_order = models.ForeignKey(
        'customer_orders.CustomerOrder',
        verbose_name='Customer Order',
        on_delete=models.SET_NULL,
        related_name='supplier_orders',
        blank=True,
        null=True,
    )
    planned_receipt_date = models.DateField(
        "План. дата приёмки", blank=True, null=True
    )
    shipping_address = models.TextField(
        "Адрес отгрузки",
        blank=True,
    )
    shipping_code = models.CharField(
        "Код точки отгрузки", max_length=100, blank=True
    )
    shipment_date = models.DateField(
        "Дата отгрузки", blank=True, null=True
    )
    sent_at = models.DateTimeField(
        "Дата отправки письма", blank=True, null=True
    )
    china_exit_date = models.DateField(
        "Дата выхода из Китая", blank=True, null=True
    )
    supplier_comment = models.TextField(
        "Комментарий для поставщика", blank=True
    )
    internal_comment = models.TextField(
        "Внутренний комментарий", blank=True
    )
    amount_cny = models.DecimalField(
        "Сумма в юанях",
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    cny_to_local_rate = models.DecimalField(
        "CNY to local rate at order creation",
        max_digits=12,
        decimal_places=2,
        default=Decimal('1.00'),
        editable=False,
    )
    company_currency_code = models.CharField(
        "Company currency at order creation",
        max_length=3,
        blank=True,
        default='',
        editable=False,
    )
    company_currency_symbol = models.CharField(
        "Company currency symbol at order creation",
        max_length=12,
        blank=True,
        default='',
        editable=False,
    )
    track_number = models.CharField(
        "Трек-номер", max_length=200, blank=True
    )
    delivery_date = models.DateField(
        "Дата получения", blank=True, null=True
    )
    logistic_invoice_no = models.CharField(
        "Номер накладной логистов", max_length=200, blank=True
    )
    production_due_date = models.DateField(
        "Срок производства до", blank=True, null=True
    )
    payment_date = models.DateField(
        "Дата оплаты", blank=True, null=True
    )
    payment_details_qr = models.ImageField(
        "QR для оплаты",
        upload_to='qr_codes/',
        blank=True,
        help_text="Подгружается из карточки поставщика",
    )

    class Meta:
        verbose_name = "Заказ поставщику"
        verbose_name_plural = "Заказы поставщику"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer_order', 'supplier']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['company', 'order_year', 'is_sample', 'order_number'], name='unique_supplier_order_number_per_kind_year'),
        ]

    def number_sequence_kind(self):
        return 'sampleorder' if self.is_sample else super().number_sequence_kind()

    def number_sequence_orders(self):
        return super().number_sequence_orders().filter(is_sample=self.is_sample)

    def save(self, *args, **kwargs):
        if not self.company_id:
            if self.supplier_id:
                self.company = self.supplier.company
            elif self.customer_id:
                self.company = self.customer.company
        if self._state.adding and not self.shipping_address:
            self.shipping_address = get_default_shipping_address(self.company if self.company_id else None)
        if self._state.adding and self.company_id:
            try:
                self.cny_to_local_rate = self.company.product_settings.cny_to_local_rate
            except ObjectDoesNotExist:
                self.cny_to_local_rate = Decimal('1.00')
            self.company_currency_code = self.company.base_currency_code or ''
            self.company_currency_symbol = (
                self.company.base_currency_symbol or self.company_currency_code
            )
        # Подставляем QR из поставщика если не указан
        if self.supplier and not self.payment_details_qr:
            self.payment_details_qr = self.supplier.qr_code_image
        super().save(*args, **kwargs)

    def __str__(self):
        return f"№{self.order_number} — {self.supplier.name}"


class SupplierOrderItem(models.Model):
    """Товары/позиции в заказе поставщику"""
    order = models.ForeignKey(
        SupplierOrder,
        verbose_name="Заказ",
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        verbose_name="Товар",
        on_delete=models.PROTECT,
        related_name='supplier_order_items'
    )
    quantity = models.DecimalField(
        "Количество",
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    defective_quantity = models.DecimalField(
        "Defective quantity",
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    unit_price_cny = models.DecimalField(
        "Purchase price per unit at order creation",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )
    unit = models.CharField(
        "Единица измерения", max_length=20, blank=True
    )
    comment = models.TextField(
        "Комментарий к позиции", blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(defective_quantity__gte=0),
                name='supplier_item_defective_quantity_nonnegative',
            ),
            models.CheckConstraint(
                condition=models.Q(defective_quantity__lte=models.F('quantity')),
                name='supplier_item_defective_quantity_lte_quantity',
            ),
        ]

    def save(self, *args, **kwargs):
        if self._state.adding and self.product_id and self.unit_price_cny is None:
            self.unit_price_cny = self.product.purchase_price or Decimal('0.00')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} — {self.quantity} {self.unit}"


class SupplierOrderAttachment(models.Model):
    order = models.ForeignKey(
        SupplierOrder,
        related_name='attachments',
        on_delete=models.CASCADE,
        verbose_name='Order'
    )
    file = models.FileField(
        upload_to='supplier_order_attachments/',
        verbose_name='Attachment'
    )
    uploaded_at = models.DateTimeField(
        'Uploaded at', auto_now_add=True
    )

    class Meta:
        verbose_name = 'Order Attachment'
        verbose_name_plural = 'Order Attachments'

    def __str__(self):
        return f"Order #{self.order.order_number} – {self.file.name}"


class SupplierOrderChangeLog(ChangeLog):
    supplier_order = models.ForeignKey(
        'SupplierOrder',
        on_delete=models.CASCADE,
        related_name='history'
    )

    def __str__(self):
        return f"{self.supplier_order.order_number}: {self.field_name} changed"
