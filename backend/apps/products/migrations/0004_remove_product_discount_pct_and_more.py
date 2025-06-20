# Generated by Django 5.1.7 on 2025-05-19 12:48

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_globalsettings_product_discount_pct_product_height_m_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='discount_pct',
        ),
        migrations.RemoveField(
            model_name='product',
            name='margin_pct',
        ),
        migrations.AddField(
            model_name='globalsettings',
            name='discount_pct',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.00'), help_text='Enter 0.10 for 10%', max_digits=5, verbose_name='Discount (%)'),
        ),
        migrations.AddField(
            model_name='globalsettings',
            name='margin_pct',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.10'), help_text='Enter 0.10 for 10%', max_digits=5, verbose_name='Margin (%)'),
        ),
    ]
