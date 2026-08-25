from django.db import migrations


LEGACY_STATUS_MAP = {
    'Waiting for delivery': 'New',
    'New Warehouse Order': 'New',
    'New Showroom Order': 'New',
    'Warehouse Packed': 'In progress',
    'Shipped from Warehouse': 'Shipped',
    'Delivered': 'Completed',
    'Cancelled at Warehouse': 'Cancelled',
}

DEFAULT_STATUS_COLORS = {
    'New': '#0d6efd',
    'In progress': '#ffc107',
    'Shipped': '#0dcaf0',
    'Completed': '#198754',
    'Cancelled': '#dc3545',
}


def forwards(apps, schema_editor):
    CustomerOrder = apps.get_model('customer_orders', 'CustomerOrder')
    CustomerOrderStatus = apps.get_model('customer_orders', 'CustomerOrderStatus')

    legacy_names = list(LEGACY_STATUS_MAP.keys())
    legacy_statuses = CustomerOrderStatus.objects.filter(name__in=legacy_names).select_related('company')

    for legacy_status in legacy_statuses:
        company = legacy_status.company
        if not company:
            continue

        target_name = LEGACY_STATUS_MAP[legacy_status.name]
        target_status, _ = CustomerOrderStatus.objects.get_or_create(
            company=company,
            name=target_name,
            defaults={'color': DEFAULT_STATUS_COLORS[target_name]},
        )
        CustomerOrder.objects.filter(company=company, status=legacy_status).update(status=target_status)

    CustomerOrderStatus.objects.filter(name__in=legacy_names).delete()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('customer_orders', '0006_customerorder_customer_comment_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
