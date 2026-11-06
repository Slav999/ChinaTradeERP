from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [('users', '0013_company_china_warehouse_address')]
    operations = [
        migrations.CreateModel(
            name='OrderNumberSequence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(max_length=32)),
                ('year', models.PositiveIntegerField()),
                ('last_number', models.PositiveBigIntegerField(default=0)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.company')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('company', 'kind', 'year'), name='unique_annual_order_sequence')]},
        ),
    ]
