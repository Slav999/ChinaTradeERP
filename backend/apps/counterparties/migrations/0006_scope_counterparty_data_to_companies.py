from django.db import migrations


DEFAULT_COUNTERPARTY_STATUSES = (
    ('New', '#6c757d'),
    ('Active', '#198754'),
    ('Blocked', '#dc3545'),
)


def forwards(apps, schema_editor):
    Company = apps.get_model('users', 'Company')
    Counterparty = apps.get_model('counterparties', 'Counterparty')
    CounterpartyStatus = apps.get_model('counterparties', 'CounterpartyStatus')

    companies = list(Company.objects.all())
    fallback_company = companies[0] if companies else None

    for counterparty in Counterparty.objects.select_related('company', 'created_by').all():
        if not counterparty.company_id:
            company = getattr(counterparty.created_by, 'company', None) or fallback_company
            if company:
                counterparty.company = company
                counterparty.save(update_fields=['company'])

    global_statuses = list(CounterpartyStatus.objects.filter(company__isnull=True))
    for status in global_statuses:
        for company in companies:
            CounterpartyStatus.objects.get_or_create(
                company=company,
                name=status.name,
                defaults={'color': status.color},
            )

    for counterparty in Counterparty.objects.select_related('company', 'status').all():
        if not counterparty.company_id or not counterparty.status_id:
            continue
        if counterparty.status.company_id == counterparty.company_id:
            continue
        status, _ = CounterpartyStatus.objects.get_or_create(
            company=counterparty.company,
            name=counterparty.status.name,
            defaults={'color': counterparty.status.color},
        )
        counterparty.status = status
        counterparty.save(update_fields=['status'])

    for company in companies:
        for name, color in DEFAULT_COUNTERPARTY_STATUSES:
            CounterpartyStatus.objects.get_or_create(
                company=company,
                name=name,
                defaults={'color': color},
            )

    CounterpartyStatus.objects.filter(company__isnull=True).delete()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('counterparties', '0005_counterpartystatus_company_and_more'),
        ('users', '0011_company_base_currency_code_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
