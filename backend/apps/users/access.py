DEFAULT_PERMISSIONS = (
    ('orders.supplier.view', 'View supplier orders'),
    ('orders.supplier.manage', 'Manage supplier orders'),
    ('orders.customer.view', 'View customer orders'),
    ('orders.customer.manage', 'Manage customer orders'),
    ('counterparties.view', 'View counterparties'),
    ('counterparties.manage', 'Manage counterparties'),
    ('products.view', 'View products'),
    ('products.manage', 'Manage products'),
    ('company.users.manage', 'Manage employees and invitations'),
    ('company.settings.manage', 'Manage company settings'),
)

DEFAULT_ROLES = (
    (
        'Company admin',
        'Full company access',
        (
            'orders.supplier.view',
            'orders.supplier.manage',
            'orders.customer.view',
            'orders.customer.manage',
            'counterparties.view',
            'counterparties.manage',
            'products.view',
            'products.manage',
            'company.users.manage',
            'company.settings.manage',
        ),
    ),
    (
        'WED manager',
        'Supplier orders and products',
        (
            'orders.supplier.view',
            'orders.supplier.manage',
            'counterparties.view',
            'products.view',
            'products.manage',
        ),
    ),
    (
        'Sales manager',
        'Customer orders and counterparties',
        (
            'orders.customer.view',
            'orders.customer.manage',
            'counterparties.view',
            'counterparties.manage',
            'products.view',
        ),
    ),
    (
        'Viewer',
        'Read-only access',
        (
            'orders.supplier.view',
            'orders.customer.view',
            'counterparties.view',
            'products.view',
        ),
    ),
)


def ensure_default_access_structure(company):
    from .models import AccessPermission, AccessRole

    permissions_by_code = {}
    for code, name in DEFAULT_PERMISSIONS:
        permission, _ = AccessPermission.objects.get_or_create(
            code=code,
            defaults={'name': name},
        )
        permissions_by_code[code] = permission

    roles_by_name = {}
    for name, description, permission_codes in DEFAULT_ROLES:
        role, _ = AccessRole.objects.get_or_create(
            company=company,
            name=name,
            defaults={'description': description, 'is_system': True},
        )
        role.permissions.set([permissions_by_code[code] for code in permission_codes])
        roles_by_name[name] = role

    return roles_by_name
