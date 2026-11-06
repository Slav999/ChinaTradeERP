DEFAULT_PERMISSIONS = (
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
            'warehouse.view',
            'warehouse.manage',
            'company.users.manage',
            'company.settings.manage',
            'pricing.purchase.view',
            'pricing.purchase.manage',
            'pricing.cost.view',
            'pricing.sale.view',
            'pricing.sale.order.manage',
            'pricing.sale.catalog.manage',
            'reports.financial.view',
        ),
    ),
    (
        'WED manager',
        'Supplier orders and products',
        (
            'orders.supplier.view',
            'orders.supplier.manage',
            'orders.customer.view',
            'counterparties.view',
            'counterparties.manage',
            'products.view',
            'products.manage',
            'warehouse.view',
            'pricing.purchase.view',
            'pricing.purchase.manage',
            'pricing.cost.view',
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
            'warehouse.view',
            'pricing.sale.view',
            'pricing.sale.order.manage',
        ),
    ),
    (
        'Financial analyst',
        'Read-only financial analytics and reports',
        (
            'orders.supplier.view',
            'orders.customer.view',
            'counterparties.view',
            'products.view',
            'warehouse.view',
            'pricing.purchase.view',
            'pricing.cost.view',
            'pricing.sale.view',
            'reports.financial.view',
        ),
    ),
    (
        'Warehouse manager',
        'Warehouse stock and operational order access',
        (
            'orders.supplier.view',
            'orders.customer.view',
            'counterparties.view',
            'products.view',
            'warehouse.view',
            'warehouse.manage',
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
            'warehouse.view',
        ),
    ),
)


def user_permission_codes(user):
    """Return the effective company permission codes for a user.

    Company administrators are the intentional override.  Legacy users that do
    not yet have an AccessRole receive operational permissions only; importantly,
    this fallback never grants access to prices or financial reports.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return set()

    if getattr(user, 'is_superuser', False) or getattr(user, 'is_company_admin', False):
        return {code for code, _name in DEFAULT_PERMISSIONS}

    role = getattr(user, 'access_role', None)
    if role and (
        role.company_id is None
        or role.company_id == getattr(user, 'company_id', None)
    ):
        return set(role.permissions.values_list('code', flat=True))

    # Transitional, deliberately non-financial fallback for pre-AccessRole
    # accounts.  An administrator can assign a standard role in the profile.
    if getattr(user, 'role', None) == 'manager':
        return {
            'orders.supplier.view',
            'orders.supplier.manage',
            'orders.customer.view',
            'orders.customer.manage',
            'counterparties.view',
            'counterparties.manage',
            'products.view',
            'products.manage',
            'warehouse.view',
            'warehouse.manage',
        }
    if getattr(user, 'role', None) == 'viewer':
        return {
            'orders.supplier.view',
            'orders.customer.view',
            'counterparties.view',
            'products.view',
            'warehouse.view',
        }
    return set()


def user_has_permission(user, code):
    return code in user_permission_codes(user)


def access_role_account_flags(access_role):
    """Map a functional AccessRole to the legacy account flags.

    The legacy role remains for compatibility, but it is never accepted from a
    client when an AccessRole is selected.
    """
    role_name = getattr(access_role, 'name', '')
    if role_name == 'Company admin':
        return 'admin', True
    if role_name in {'WED manager', 'Sales manager', 'Warehouse manager'}:
        return 'manager', False
    return 'viewer', False


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
        if role.description != description or not role.is_system:
            role.description = description
            role.is_system = True
            role.save(update_fields=['description', 'is_system'])
        role.permissions.set([permissions_by_code[code] for code in permission_codes])
        roles_by_name[name] = role

    return roles_by_name
