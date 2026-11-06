from django.db import migrations, models
import pytz


def populate_years(apps, schema_editor):
    Order = apps.get_model('customer_orders', 'CustomerOrder')
    Sequence = apps.get_model('core', 'OrderNumberSequence')
    alias = schema_editor.connection.alias
    counters = {}
    primary = {'KZ': 'Asia/Almaty', 'RU': 'Europe/Moscow', 'CN': 'Asia/Shanghai', 'US': 'America/New_York'}
    for order in Order.objects.using(alias).select_related('company').iterator():
        country = str(order.company.business_country or 'KZ')
        zone = primary.get(country) or next(iter(pytz.country_timezones.get(country, [])), 'UTC')
        year = (order.created_at or order.company.created_at).astimezone(pytz.timezone(zone)).year
        Order.objects.using(alias).filter(pk=order.pk).update(order_year=year)
        key = (order.company_id, year)
        number = order.order_number
        counters[key] = max(counters.get(key, 0), int(number) if number.isascii() and number.isdigit() else 0)
    for (company_id, year), number in counters.items():
        Sequence.objects.using(alias).update_or_create(company_id=company_id, kind='customerorder', year=year,
                                                       defaults={'last_number': number})


class Migration(migrations.Migration):
    dependencies = [('customer_orders', '0008_customerorder_sent_at'), ('core', '0001_initial')]
    operations = [
        migrations.AddField(model_name='customerorder', name='order_year', field=models.PositiveIntegerField(null=True, editable=False)),
        migrations.RunPython(populate_years, migrations.RunPython.noop),
        migrations.AlterField(model_name='customerorder', name='order_year', field=models.PositiveIntegerField(editable=False)),
        migrations.RemoveConstraint(model_name='customerorder', name='unique_customer_order_number_per_company'),
        migrations.AddConstraint(model_name='customerorder', constraint=models.UniqueConstraint(fields=('company', 'order_year', 'order_number'), name='unique_customer_order_number_per_year')),
    ]
