DEFAULT_PRODUCT_UNITS = (
    ('pcs', 'Pieces'),
    ('kg', 'Kilograms'),
    ('g', 'Grams'),
    ('m', 'Meters'),
    ('m2', 'Square meters'),
    ('m3', 'Cubic meters'),
    ('box', 'Boxes'),
    ('set', 'Sets'),
)

DEFAULT_PRODUCT_CATEGORIES = (
    ('General', None),
)

DEFAULT_COUNTERPARTY_STATUSES = (
    ('New', '#6c757d'),
    ('Active', '#198754'),
    ('Blocked', '#dc3545'),
)

DEFAULT_CUSTOMER_ORDER_STATUSES = (
    ('New', '#0d6efd'),
    ('In progress', '#ffc107'),
    ('Shipped', '#0dcaf0'),
    ('Completed', '#198754'),
    ('Cancelled', '#dc3545'),
)

DEFAULT_SUPPLIER_ORDER_STATUSES = (
    ('New', '#0d6efd'),
    ('In production', '#ffc107'),
    ('In transit', '#0dcaf0'),
    ('Received', '#198754'),
    ('Cancelled', '#dc3545'),
)


def ensure_default_company_directories(company):
    from counterparties.models import CounterpartyStatus
    from customer_orders.models import CustomerOrderStatus, ShippingAddress as CustomerShippingAddress
    from products.models import ProductCategory, Unit
    from supplier_orders.models import SupplierOrderStatus, ShippingAddress as SupplierShippingAddress

    for name, margin_pct in DEFAULT_PRODUCT_CATEGORIES:
        ProductCategory.objects.get_or_create(
            company=company,
            name=name,
            defaults={'margin_pct': margin_pct},
        )

    for name, _label in DEFAULT_PRODUCT_UNITS:
        Unit.objects.get_or_create(company=company, name=name)

    for name, color in DEFAULT_COUNTERPARTY_STATUSES:
        CounterpartyStatus.objects.get_or_create(
            company=company,
            name=name,
            defaults={'color': color},
        )

    for name, color in DEFAULT_CUSTOMER_ORDER_STATUSES:
        CustomerOrderStatus.objects.get_or_create(
            company=company,
            name=name,
            defaults={'color': color},
        )

    for name, color in DEFAULT_SUPPLIER_ORDER_STATUSES:
        SupplierOrderStatus.objects.get_or_create(
            company=company,
            name=name,
            defaults={'color': color},
        )

    CustomerShippingAddress.objects.get_or_create(company=company)
    SupplierShippingAddress.objects.get_or_create(company=company)
