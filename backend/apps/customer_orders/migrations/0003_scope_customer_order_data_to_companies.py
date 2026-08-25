from django.db import migrations


DEFAULT_CUSTOMER_ORDER_STATUSES = (
    ('New', '#0d6efd'),
    ('In progress', '#ffc107'),
    ('Shipped', '#0dcaf0'),
    ('Completed', '#198754'),
    ('Cancelled', '#dc3545'),
)


def forwards(apps, schema_editor):
    Company = apps.get_model('users', 'Company')
    CustomerOrder = apps.get_model('customer_orders', 'CustomerOrder')
    CustomerOrderStatus = apps.get_model('customer_orders', 'CustomerOrderStatus')
    ShippingAddress = apps.get_model('customer_orders', 'ShippingAddress')

    companies = list(Company.objects.all())
    fallback_company = companies[0] if companies else None

    global_statuses = list(CustomerOrderStatus.objects.filter(company__isnull=True))
    for status in global_statuses:
        for company in companies:
            CustomerOrderStatus.objects.get_or_create(
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

    for order in CustomerOrder.objects.select_related('customer', 'created_by', 'status').all():
        company = order.company
        if not company:
            company = getattr(order.customer, 'company', None) or getattr(order.created_by, 'company', None) or fallback_company
            if company:
                order.company = company

        if company and order.status_id and order.status.company_id != company.id:
            status, _ = CustomerOrderStatus.objects.get_or_create(
                company=company,
                name=order.status.name,
                defaults={'color': order.status.color},
            )
            order.status = status

        order.save(update_fields=['company', 'status'])

    for company in companies:
        for name, color in DEFAULT_CUSTOMER_ORDER_STATUSES:
            CustomerOrderStatus.objects.get_or_create(
                company=company,
                name=name,
                defaults={'color': color},
            )

    CustomerOrderStatus.objects.filter(company__isnull=True).delete()
    ShippingAddress.objects.filter(company__isnull=True).delete()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('customer_orders', '0002_customerorder_company_customerorderstatus_company_and_more'),
        ('counterparties', '0006_scope_counterparty_data_to_companies'),
        ('users', '0011_company_base_currency_code_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
