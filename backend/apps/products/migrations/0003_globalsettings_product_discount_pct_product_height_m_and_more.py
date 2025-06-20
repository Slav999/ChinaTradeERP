# Generated by Django 5.1.7 on 2025-05-19 09:45

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_productchangelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='GlobalSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cny_to_local_rate', models.DecimalField(decimal_places=6, help_text='Local currency units per 1 CNY', max_digits=12, verbose_name='CNY → Local Rate')),
                ('usd_to_local_rate', models.DecimalField(decimal_places=6, help_text='Local currency units per 1 USD', max_digits=12, verbose_name='USD → Local Rate')),
                ('logistics_cost_per_kg_usd', models.DecimalField(decimal_places=2, help_text='Cost of logistics per kilogram in USD', max_digits=10, verbose_name='Logistics Cost (USD/kg)')),
                ('retail_tax_pct', models.DecimalField(decimal_places=4, default=Decimal('0.08'), help_text='Enter 0.08 for 8%', max_digits=5, verbose_name='Retail Tax (%)')),
                ('acquiring_pct', models.DecimalField(decimal_places=4, default=Decimal('0.01'), help_text='Enter 0.01 for 1%', max_digits=5, verbose_name='Acquiring Fee (%)')),
                ('packaging_pct', models.DecimalField(decimal_places=4, default=Decimal('0.01'), help_text='Enter 0.01 for 1%', max_digits=5, verbose_name='Packaging Fee (%)')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='discount_pct',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.00'), help_text='Enter 0.10 for 10%', max_digits=5, verbose_name='Discount (%)'),
        ),
        migrations.AddField(
            model_name='product',
            name='height_m',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True, verbose_name='Box height (m)'),
        ),
        migrations.AddField(
            model_name='product',
            name='length_m',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True, verbose_name='Box length (m)'),
        ),
        migrations.AddField(
            model_name='product',
            name='margin_pct',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.10'), help_text='Enter 0.10 for 10%', max_digits=5, verbose_name='Margin (%)'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_yuan',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Price per unit (CNY)'),
        ),
        migrations.AddField(
            model_name='product',
            name='units_per_package',
            field=models.PositiveIntegerField(default=1, help_text='Number of items in one package/box', verbose_name='Units per package'),
        ),
        migrations.AddField(
            model_name='product',
            name='weight_kg',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True, verbose_name='Weight per unit (kg)'),
        ),
        migrations.AddField(
            model_name='product',
            name='width_m',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True, verbose_name='Box width (m)'),
        ),
        migrations.AlterField(
            model_name='product',
            name='sale_price',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Sale Price (Local)'),
        ),
    ]
