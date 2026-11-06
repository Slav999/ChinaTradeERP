DEFAULT_DEPARTMENTS = (
    ('ВЭД', 'Foreign trade', ('VED', 'VET', 'WED', 'ВЕТ')),
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


def merge_foreign_trade_departments():
    """Merge legacy aliases within each company, preserving all department links."""
    from django.db import transaction
    from .models import CompanyMembership, CustomUser, Department, Invitation

    ru, en, aliases = DEFAULT_DEPARTMENTS[0]
    names = {name.casefold() for name in (ru, en, *aliases)}
    merged = 0
    with transaction.atomic():
        companies = {}
        for department in Department.objects.select_for_update().order_by('pk'):
            if department.name.strip().casefold() in names:
                companies.setdefault(department.company_id, []).append(department)
        for departments in companies.values():
            departments.sort(key=lambda item: (item.is_archived, item.name != ru, item.pk))
            canonical = departments[0]
            if not canonical.translations:
                canonical.translations = {'ru': ru, 'en': en}
                canonical.save(update_fields=['translations'])
            for duplicate in departments[1:]:
                CompanyMembership.objects.filter(department=duplicate).update(department=canonical)
                Invitation.objects.filter(department=duplicate).update(department=canonical)
                CustomUser.objects.filter(department_ref=duplicate).update(
                    department_ref=canonical, department=canonical.name,
                )
                duplicate.delete()
                merged += 1
    return merged
