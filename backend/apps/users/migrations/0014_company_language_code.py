from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_company_china_warehouse_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='language_code',
            field=models.CharField(
                choices=[('ru', 'Русский'), ('en', 'English')],
                default='ru',
                max_length=5,
            ),
        ),
    ]
