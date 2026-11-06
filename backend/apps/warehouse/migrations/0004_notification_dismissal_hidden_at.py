from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0003_stockalert_stockalertdismissal_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockalertdismissal',
            name='hidden_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='stockcontroldismissal',
            name='hidden_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
