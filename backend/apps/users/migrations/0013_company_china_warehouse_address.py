from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_company_address_company_bank_details_company_logo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='china_warehouse_address',
            field=models.TextField(blank=True),
        ),
    ]
