from django.db import migrations


DEFAULT_DEPARTMENTS = (
    ('ВЭД', 'Foreign trade', ('VED', 'VET', 'ВЕТ')),
    ('Отдел продаж', 'Sales', ('Продажи', 'Sales department')),
    ('Склад', 'Warehouse', ()),
    ('Бухгалтерия и финансы', 'Accounting and finance', ()),
)


def seed_departments(model, company_id):
    """Keep existing names and links; enrich recognised departments only."""
    for ru, en, aliases in DEFAULT_DEPARTMENTS:
        department = next((
            item for item in model.objects.filter(company_id=company_id)
            if item.name.casefold() in {name.casefold() for name in (ru, en, *aliases)}
        ), None)
        if department is None:
            model.objects.create(
                company_id=company_id, name=ru, translations={'ru': ru, 'en': en},
            )
        elif not department.translations:
            department.translations = {'ru': ru, 'en': en}
            department.save(update_fields=['translations'])


def seed_existing_companies(apps, schema_editor):
    Company = apps.get_model('users', 'Company')
    Department = apps.get_model('users', 'Department')
    for company_id in Company.objects.values_list('pk', flat=True).iterator():
        seed_departments(Department, company_id)


class Migration(migrations.Migration):
    dependencies = [('users', '0016_department_translations_and_archive')]
    operations = [migrations.RunPython(seed_existing_companies, migrations.RunPython.noop)]
