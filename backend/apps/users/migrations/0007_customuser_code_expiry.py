from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_customuser_profile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='reset_code_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='verification_code_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
