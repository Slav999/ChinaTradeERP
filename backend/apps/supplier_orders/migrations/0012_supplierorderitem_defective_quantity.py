from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('supplier_orders', '0011_annual_order_numbers')]

    operations = [
        migrations.AddField(
            model_name='supplierorderitem',
            name='defective_quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Defective quantity'),
        ),
        migrations.AddConstraint(
            model_name='supplierorderitem',
            constraint=models.CheckConstraint(
                condition=models.Q(defective_quantity__gte=0),
                name='supplier_item_defective_quantity_nonnegative',
            ),
        ),
        migrations.AddConstraint(
            model_name='supplierorderitem',
            constraint=models.CheckConstraint(
                condition=models.Q(defective_quantity__lte=models.F('quantity')),
                name='supplier_item_defective_quantity_lte_quantity',
            ),
        ),
    ]
