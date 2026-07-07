from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_alter_globalsettings_cny_to_local_rate_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='GlobalSettings',
            new_name='CompanySettings',
        ),
    ]
