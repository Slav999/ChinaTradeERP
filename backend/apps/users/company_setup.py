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
    ('new', 'New', 'Новый', '#6c757d'),
    ('active', 'Active', 'Активный', '#198754'),
    ('blocked', 'Blocked', 'Заблокирован', '#dc3545'),
)

DEFAULT_CUSTOMER_ORDER_STATUSES = (
    ('new', 'New', 'Новый', '#0d6efd'),
    ('in_progress', 'In progress', 'В работе', '#ffc107'),
    ('shipped', 'Shipped', 'Отгружен', '#0dcaf0'),
    ('completed', 'Completed', 'Завершён', '#198754'),
    ('cancelled', 'Cancelled', 'Отменён', '#dc3545'),
)

DEFAULT_SUPPLIER_ORDER_STATUSES = (
    ('new', 'New', 'Новый', '#0d6efd'),
    ('in_production', 'In production', 'В производстве', '#ffc107'),
    ('in_transit', 'In transit', 'В пути', '#0dcaf0'),
    ('received', 'Received', 'Получен', '#198754'),
    ('cancelled', 'Cancelled', 'Отменён', '#dc3545'),
)


def ensure_default_company_directories(company):
    from .departments import seed_departments
    from .models import Department
    from counterparties.models import CounterpartyStatus
    from customer_orders.models import CustomerOrderStatus, ShippingAddress as CustomerShippingAddress
    from products.models import ProductCategory, Unit
    from supplier_orders.models import SupplierOrderStatus, ShippingAddress as SupplierShippingAddress

    seed_departments(Department, company.pk)

    for name, margin_pct in DEFAULT_PRODUCT_CATEGORIES:
        ProductCategory.objects.get_or_create(
            company=company,
            name=name,
            defaults={'margin_pct': margin_pct},
        )

    for name, _label in DEFAULT_PRODUCT_UNITS:
        Unit.objects.get_or_create(company=company, name=name)

    for code, name_en, name_ru, color in DEFAULT_COUNTERPARTY_STATUSES:
        CounterpartyStatus.objects.get_or_create(
            company=company,
            code=code,
            defaults={
                'name': name_en, 'translations': {'en': name_en, 'ru': name_ru},
                'is_system': True, 'color': color,
            },
        )

    for code, name_en, name_ru, color in DEFAULT_CUSTOMER_ORDER_STATUSES:
        CustomerOrderStatus.objects.get_or_create(
            company=company,
            code=code,
            defaults={
                'name': name_en, 'translations': {'en': name_en, 'ru': name_ru},
                'is_system': True, 'color': color,
            },
        )

    for code, name_en, name_ru, color in DEFAULT_SUPPLIER_ORDER_STATUSES:
        SupplierOrderStatus.objects.get_or_create(
            company=company,
            code=code,
            defaults={
                'name': name_en, 'translations': {'en': name_en, 'ru': name_ru},
                'is_system': True, 'color': color,
            },
        )

    CustomerShippingAddress.objects.get_or_create(company=company)
    SupplierShippingAddress.objects.get_or_create(company=company)
