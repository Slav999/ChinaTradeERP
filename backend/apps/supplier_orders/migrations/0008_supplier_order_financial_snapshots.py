from decimal import Decimal

from django.db import migrations, models


def backfill_financial_snapshots(apps, schema_editor):
    SupplierOrder = apps.get_model('supplier_orders', 'SupplierOrder')
    SupplierOrderItem = apps.get_model('supplier_orders', 'SupplierOrderItem')
    CompanySettings = apps.get_model('products', 'CompanySettings')

    settings_by_company = {
        settings.company_id: settings.cny_to_local_rate
        for settings in CompanySettings.objects.all().iterator()
    }

    for order in SupplierOrder.objects.select_related('company').iterator():
        order.cny_to_local_rate = settings_by_company.get(
            order.company_id,
            Decimal('1.00'),
        )
        order.company_currency_code = order.company.base_currency_code or ''
        order.company_currency_symbol = (
            order.company.base_currency_symbol or order.company_currency_code
        )
        order.save(update_fields=[
            'cny_to_local_rate',
            'company_currency_code',
            'company_currency_symbol',
        ])

    for item in SupplierOrderItem.objects.select_related('product').iterator():
        item.unit_price_cny = item.product.purchase_price or Decimal('0.00')
        item.save(update_fields=['unit_price_cny'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0018_product_is_stock_item'),
        ('supplier_orders', '0007_supplierorder_internal_comment'),
        ('users', '0012_company_address_company_bank_details_company_logo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplierorder',
            name='cny_to_local_rate',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('1.00'),
                editable=False,
                max_digits=12,
                verbose_name='CNY to local rate at order creation',
            ),
        ),
        migrations.AddField(
            model_name='supplierorder',
            name='company_currency_code',
            field=models.CharField(
                blank=True,
                default='',
                editable=False,
                max_length=3,
                verbose_name='Company currency at order creation',
            ),
        ),
        migrations.AddField(
            model_name='supplierorder',
            name='company_currency_symbol',
            field=models.CharField(
                blank=True,
                default='',
                editable=False,
                max_length=12,
                verbose_name='Company currency symbol at order creation',
            ),
        ),
        migrations.AddField(
            model_name='supplierorderitem',
            name='unit_price_cny',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                editable=False,
                max_digits=10,
                verbose_name='Purchase price per unit at order creation',
            ),
        ),
        migrations.RunPython(backfill_financial_snapshots, migrations.RunPython.noop),
    ]
