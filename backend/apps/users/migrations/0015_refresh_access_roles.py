from django.db import migrations


PERMISSIONS = (
    ('orders.supplier.view', 'View supplier orders'),
    ('orders.supplier.manage', 'Manage supplier orders'),
    ('orders.customer.view', 'View customer orders'),
    ('orders.customer.manage', 'Manage customer orders'),
    ('counterparties.view', 'View counterparties'),
    ('counterparties.manage', 'Manage counterparties'),
    ('products.view', 'View products'),
    ('products.manage', 'Manage products'),
    ('warehouse.view', 'View warehouse'),
    ('warehouse.manage', 'Manage warehouse'),
    ('company.users.manage', 'Manage employees and invitations'),
    ('company.settings.manage', 'Manage company settings'),
    ('pricing.purchase.view', 'View purchase prices'),
    ('pricing.purchase.manage', 'Manage purchase prices'),
    ('pricing.cost.view', 'View calculated cost prices'),
    ('pricing.sale.view', 'View sale prices'),
    ('pricing.sale.order.manage', 'Manage sale prices and discounts in customer orders'),
    ('pricing.sale.catalog.manage', 'Manage the default catalog sale price'),
    ('reports.financial.view', 'View and export financial reports'),
)


ROLES = (
    ('Company admin', 'Full company access', tuple(code for code, _name in PERMISSIONS)),
    ('WED manager', 'Supplier orders and products', (
        'orders.supplier.view', 'orders.supplier.manage', 'orders.customer.view',
        'counterparties.view', 'counterparties.manage', 'products.view', 'products.manage',
        'warehouse.view', 'pricing.purchase.view', 'pricing.purchase.manage', 'pricing.cost.view',
    )),
    ('Sales manager', 'Customer orders and counterparties', (
        'orders.customer.view', 'orders.customer.manage', 'counterparties.view',
        'counterparties.manage', 'products.view', 'warehouse.view', 'pricing.sale.view',
        'pricing.sale.order.manage',
    )),
    ('Financial analyst', 'Read-only financial analytics and reports', (
        'orders.supplier.view', 'orders.customer.view', 'counterparties.view',
        'products.view', 'warehouse.view', 'pricing.purchase.view', 'pricing.cost.view',
        'pricing.sale.view', 'reports.financial.view',
    )),
    ('Warehouse manager', 'Warehouse stock and operational order access', (
        'orders.supplier.view', 'orders.customer.view', 'counterparties.view',
        'products.view', 'warehouse.view', 'warehouse.manage',
    )),
    ('Viewer', 'Read-only access', (
        'orders.supplier.view', 'orders.customer.view', 'counterparties.view',
        'products.view', 'warehouse.view',
    )),
)


def refresh_access_roles(apps, schema_editor):
    Company = apps.get_model('users', 'Company')
    AccessPermission = apps.get_model('users', 'AccessPermission')
    AccessRole = apps.get_model('users', 'AccessRole')

    permissions = {}
    for code, name in PERMISSIONS:
        permission, _created = AccessPermission.objects.get_or_create(
            code=code,
            defaults={'name': name},
        )
        permissions[code] = permission

    for company in Company.objects.iterator():
        for name, description, codes in ROLES:
            role, _created = AccessRole.objects.get_or_create(
                company=company,
                name=name,
                defaults={'description': description, 'is_system': True},
            )
            role.description = description
            role.is_system = True
            role.save(update_fields=['description', 'is_system'])
            role.permissions.set([permissions[code] for code in codes])


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0014_company_language_code'),
    ]

    operations = [
        migrations.RunPython(refresh_access_roles, migrations.RunPython.noop),
    ]
