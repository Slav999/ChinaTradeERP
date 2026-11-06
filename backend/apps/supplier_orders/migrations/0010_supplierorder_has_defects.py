from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('supplier_orders', '0009_supplierorder_sent_at')]

    operations = [
        migrations.AddField(
            model_name='supplierorder',
            name='has_defects',
            field=models.BooleanField(default=False, verbose_name='Has defects'),
        ),
    ]
