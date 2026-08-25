from django.db import migrations


DEFAULT_SUPPLIER_ORDER_STATUSES = (
    ('New', '#0d6efd'),
    ('In production', '#ffc107'),
    ('In transit', '#0dcaf0'),
    ('Received', '#198754'),
    ('Cancelled', '#dc3545'),
)


def forwards(apps, schema_editor):
    Company = apps.get_model('users', 'Company')
    SupplierOrder = apps.get_model('supplier_orders', 'SupplierOrder')
    SupplierOrderStatus = apps.get_model('supplier_orders', 'SupplierOrderStatus')
    ShippingAddress = apps.get_model('supplier_orders', 'ShippingAddress')

    companies = list(Company.objects.all())
    fallback_company = companies[0] if companies else None

    global_statuses = list(SupplierOrderStatus.objects.filter(company__isnull=True))
    for status in global_statuses:
        for company in companies:
            SupplierOrderStatus.objects.get_or_create(
                company=company,
                name=status.name,
                defaults={'color': status.color},
            )

    global_addresses = list(ShippingAddress.objects.filter(company__isnull=True))
    default_address = global_addresses[0].default_shipping_address if global_addresses else ''
    for company in companies:
        ShippingAddress.objects.get_or_create(
            company=company,
            defaults={'default_shipping_address': default_address},
        )

    for order in SupplierOrder.objects.select_related('supplier', 'customer', 'created_by', 'status', 'customer_order').all():
        company = order.company
        if not company:
            company = (
                getattr(order.supplier, 'company', None)
                or getattr(order.customer, 'company', None)
                or getattr(order.customer_order, 'company', None)
                or getattr(order.created_by, 'company', None)
                or fallback_company
            )
            if company:
                order.company = company

        if company and order.status_id and order.status.company_id != company.id:
            status, _ = SupplierOrderStatus.objects.get_or_create(
                company=company,
                name=order.status.name,
                defaults={'color': order.status.color},
            )
            order.status = status

        order.save(update_fields=['company', 'status'])

    for company in companies:
        for name, color in DEFAULT_SUPPLIER_ORDER_STATUSES:
            SupplierOrderStatus.objects.get_or_create(
                company=company,
                name=name,
                defaults={'color': color},
            )

    SupplierOrderStatus.objects.filter(company__isnull=True).delete()
    ShippingAddress.objects.filter(company__isnull=True).delete()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('supplier_orders', '0004_shippingaddress_company_supplierorder_company_and_more'),
        ('customer_orders', '0003_scope_customer_order_data_to_companies'),
        ('counterparties', '0006_scope_counterparty_data_to_companies'),
        ('users', '0011_company_base_currency_code_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
