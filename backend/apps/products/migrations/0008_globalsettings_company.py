from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


DEFAULTS = {
    'cny_to_local_rate': Decimal('1.000000'),
    'usd_to_local_rate': Decimal('1.000000'),
    'logistics_cost_per_kg_usd': Decimal('0.00'),
    'retail_tax_pct': Decimal('0.08'),
    'acquiring_pct': Decimal('0.01'),
    'packaging_pct': Decimal('0.01'),
    'margin_pct': Decimal('0.50'),
    'discount_pct': Decimal('0.10'),
}


def copy_settings_to_companies(apps, schema_editor):
    Company = apps.get_model('users', 'Company')
    GlobalSettings = apps.get_model('products', 'GlobalSettings')

    existing = GlobalSettings.objects.order_by('id').first()
    base_values = DEFAULTS.copy()
    if existing:
        for field in base_values:
            base_values[field] = getattr(existing, field)

    for company in Company.objects.all():
        settings = GlobalSettings.objects.filter(company=company).order_by('id').first()
        if not settings:
            settings = GlobalSettings(company=company)
        for field, value in base_values.items():
            setattr(settings, field, value)
        settings.save()

        GlobalSettings.objects.filter(company=company).exclude(id=settings.id).delete()

    GlobalSettings.objects.filter(company__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_companymembership'),
        ('products', '0007_product_archive_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalsettings',
            name='company',
            field=models.OneToOneField(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='product_settings',
                to='users.company',
            ),
        ),
        migrations.RunPython(copy_settings_to_companies, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='globalsettings',
            name='company',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='product_settings',
                to='users.company',
            ),
        ),
        migrations.AlterField(
            model_name='globalsettings',
            name='cny_to_local_rate',
            field=models.DecimalField(
                decimal_places=6,
                default=Decimal('1.000000'),
                help_text='Local currency units per 1 CNY',
                max_digits=12,
                verbose_name='CNY в†’ Local Rate',
            ),
        ),
        migrations.AlterField(
            model_name='globalsettings',
            name='usd_to_local_rate',
            field=models.DecimalField(
                decimal_places=6,
                default=Decimal('1.000000'),
                help_text='Local currency units per 1 USD',
                max_digits=12,
                verbose_name='USD в†’ Local Rate',
            ),
        ),
        migrations.AlterField(
            model_name='globalsettings',
            name='logistics_cost_per_kg_usd',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Cost of logistics per kilogram in USD',
                max_digits=10,
                verbose_name='Logistics Cost (USD/kg)',
            ),
        ),
    ]
