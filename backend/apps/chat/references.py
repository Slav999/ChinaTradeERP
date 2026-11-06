from django.apps import apps
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError
from users.access import user_has_permission


REFERENCES = {
    'customer_order': ('customer_orders.CustomerOrder', 'orders.customer.view', 'Заказ покупателя'),
    'supplier_order': ('supplier_orders.SupplierOrder', 'orders.supplier.view', 'Заказ поставщику'),
    'product': ('products.Product', 'products.view', 'Товар'),
    'counterparty': ('counterparties.Counterparty', 'counterparties.view', 'Контрагент'),
}


def reference_queryset(user, kind):
    if kind not in REFERENCES:
        raise ValidationError('Unknown reference type.')
    model, permission, _ = REFERENCES[kind]
    if not user_has_permission(user, permission):
        raise PermissionDenied('No access to this type of record.')
    return apps.get_model(model).objects.filter(company_id=user.company_id)


def reference_data(obj, kind):
    label = REFERENCES[kind][2]
    if kind in ('product', 'counterparty'):
        title = obj.name
        path = '/products' if kind == 'product' else '/counterparty'
        route = {'path': path, 'query': {'chatRecord': str(obj.pk)}}
    else:
        title = f'{label} №{obj.order_number} / {obj.order_year}'
        path = '/customer-orders' if kind == 'customer_order' else ('/samples-trips' if obj.is_sample else '/supplier-orders')
        route = {'path': f'{path}/{obj.pk}'}
    return {'type': kind, 'id': obj.pk, 'label': label, 'title': title, 'route': route}


def visible_reference(user, kind, pk):
    if not kind or not pk:
        return None
    try:
        obj = reference_queryset(user, kind).filter(pk=pk).first()
    except (PermissionDenied, ValidationError):
        obj = None
    return reference_data(obj, kind) if obj else {'unavailable': True, 'title': 'Объект недоступен'}


def reference_search_queryset(user, kind, search):
    qs = reference_queryset(user, kind)
    search = search.strip()
    if not search:
        return qs.none()
    if kind in ('product', 'counterparty'):
        condition = Q(name__icontains=search)
        if kind == 'product':
            condition |= Q(sku__icontains=search)
    else:
        condition = Q(order_number__icontains=search)
        if kind == 'customer_order':
            condition |= Q(customer__name__icontains=search)
        else:
            condition |= Q(supplier__name__icontains=search) | Q(customer__name__icontains=search) | Q(trip_name__icontains=search)
        condition |= Q(items__product__sku__icontains=search) | Q(items__product__name__icontains=search)
    if search.isdecimal() and len(search) < 19:
        condition |= Q(pk=int(search))
    return qs.filter(condition).distinct()


def search_references(user, kind, search):
    return [reference_data(obj, kind) for obj in reference_search_queryset(user, kind, search).order_by('-pk')[:5]]


def message_search_condition(user, search):
    condition = (Q(text__icontains=search) | Q(attachments__name__icontains=search) |
                 Q(sender__first_name__icontains=search) | Q(sender__last_name__icontains=search) |
                 Q(sender__middle_name__icontains=search) | Q(sender__username__icontains=search))
    for kind in REFERENCES:
        try:
            ids = reference_search_queryset(user, kind, search).order_by().values('pk')
            condition |= Q(reference_type=kind, reference_id__in=ids)
        except PermissionDenied:
            pass
    return condition
