from decimal import Decimal

from django.db import migrations


ZERO = Decimal('0.00')
CENT = Decimal('0.01')


def recalculate_automatic_prices(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    CompanySettings = apps.get_model('products', 'CompanySettings')
    settings_by_company = {
        settings.company_id: settings
        for settings in CompanySettings.objects.all()
    }

    for product in Product.objects.filter(sale_price_mode='automatic').select_related('category').iterator():
        settings = settings_by_company.get(product.company_id)
        if settings is None:
            continue

        purchase_cost = (product.purchase_price or ZERO) * settings.cny_to_local_rate
        international_logistics = (
            (product.weight_kg or ZERO)
            * settings.logistics_cost_per_kg_usd
            * settings.usd_to_local_rate
        )
        landed_cost = purchase_cost + international_logistics
        after_customs = landed_cost + landed_cost * settings.customs_duty_pct
        before_packaging = after_customs + after_customs * settings.internal_logistics_pct
        cost_price = before_packaging + before_packaging * settings.packaging_pct
        margin = (
            product.category.margin_pct
            if product.category_id and product.category.margin_pct is not None
            else settings.margin_pct
        )
        with_margin = cost_price * (Decimal('1.00') + margin)
        sale_price = with_margin * (
            Decimal('1.00') + settings.retail_tax_pct + settings.acquiring_pct
        )
        product.sale_price = sale_price.quantize(CENT)
        product.save(update_fields=['sale_price'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0022_companysettings_customs_duty_pct_and_more'),
    ]

    operations = [
        migrations.RunPython(recalculate_automatic_prices, migrations.RunPython.noop),
    ]
