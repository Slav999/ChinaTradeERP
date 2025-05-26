from django.db import models
from core.models import BaseModel, ChangeLog
from counterparties.models import Counterparty
from products.models import Product
from django.db.models import Max


def get_default_shipping_address():
    """
    Возвращает дефолтный адрес из единственной записи ShippingAddress (если есть).
    """
    addr = ShippingAddress.objects.first()
    return addr.default_shipping_address if addr else ''


class SupplierOrderStatus(models.Model):
    """Статусы заказа поставщику (админ может добавлять/редактировать)"""
    name = models.CharField("Название", max_length=100, unique=True)
    color = models.CharField("Цвет (hex)", max_length=7, default="#007bff")

    class Meta:
        verbose_name = "Статус заказа поставщику"
        verbose_name_plural = "Статусы заказа поставщику"

    def __str__(self):
        return self.name


class ShippingAddress(models.Model):
    """Настройки: дефолтный адрес отгрузки"""
    default_shipping_address = models.TextField(
        "Адрес отгрузки по умолчанию", blank=True
    )

    def __str__(self):
        return self.default_shipping_address or '-'


class SupplierOrder(BaseModel):
    """Заказ поставщику"""
    order_number = models.CharField(
        "Номер заказа", max_length=50, unique=True
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
    planned_receipt_date = models.DateField(
        "План. дата приёмки", blank=True, null=True
    )
    shipping_address = models.TextField(
        "Адрес отгрузки",
        default=get_default_shipping_address,
        blank=True,
    )
    shipping_code = models.CharField(
        "Код точки отгрузки", max_length=100, blank=True
    )
    shipment_date = models.DateField(
        "Дата отгрузки", blank=True, null=True
    )
    china_exit_date = models.DateField(
        "Дата выхода из Китая", blank=True, null=True
    )
    supplier_comment = models.TextField(
        "Комментарий для поставщика", blank=True
    )
    amount_cny = models.DecimalField(
        "Сумма в юанях",
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
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

    def save(self, *args, **kwargs):
        # Подставляем дефолтный адрес если не указан
        if not self.shipping_address:
            self.shipping_address = get_default_shipping_address()
        if not self.order_number:
            last_num = (
                    SupplierOrder.objects
                    .aggregate(Max('id'))
                    .get('id__max') or 0
            )
            self.order_number = str(last_num + 1)
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
    unit = models.CharField(
        "Единица измерения", max_length=20, blank=True
    )
    comment = models.TextField(
        "Комментарий к позиции", blank=True
    )

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