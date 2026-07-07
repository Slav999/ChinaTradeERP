from django.db import migrations, models


def set_initial_roles(apps, schema_editor):
    Counterparty = apps.get_model('counterparties', 'Counterparty')
    Counterparty.objects.filter(type='china').update(is_supplier=True)
    Counterparty.objects.filter(type='local').update(is_customer=True)


def unset_initial_roles(apps, schema_editor):
    Counterparty = apps.get_model('counterparties', 'Counterparty')
    Counterparty.objects.update(is_supplier=False, is_customer=False)


class Migration(migrations.Migration):

    dependencies = [
        ('counterparties', '0003_alter_counterparty_created_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='counterparty',
            name='is_supplier',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='is_customer',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_initial_roles, unset_initial_roles),
    ]
