from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from supplier_orders.models import (
    SupplierOrder,
    SupplierOrderItem,
    SupplierOrderStatus,
)
from warehouse.services import sync_supplier_order


class SupplierOrderCreationError(Exception):
    def __init__(self, detail, status_code=400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _money(value):
    return str((value or Decimal('0.00')).quantize(Decimal('0.01')))


def _company_currency_payload(order):
    company = order.customer.company if getattr(order, 'customer_id', None) else None
    if not company and getattr(order, 'supplier_id', None):
        company = order.supplier.company
    if not company:
        return {
            'company_currency_code': 'KZT',
            'company_currency_symbol': '₸',
            'cny_to_local_rate': Decimal('1.000000'),
        }
    try:
        settings = company.product_settings
        cny_rate = settings.cny_to_local_rate
    except Exception:
        cny_rate = Decimal('1.000000')
    return {
        'company_currency_code': company.base_currency_code or 'KZT',
        'company_currency_symbol': company.base_currency_symbol or company.base_currency_code or 'KZT',
        'cny_to_local_rate': cny_rate,
    }


def _status_payload(status):
    if not status:
        return None
    return {
        'name': status.name,
        'color': status.color,
    }


def customer_order_total_after_discount(order):
    total = Decimal('0.00')
    for item in order.items.select_related('product'):
        unit_price = item.product.sale_price or Decimal('0.00')
        quantity = item.quantity or Decimal('0.00')
        line_discount = item.discount_pct or Decimal('0.0000')
        total += unit_price * quantity * (Decimal('1.0000') - line_discount)

    order_discount = order.discount_pct or Decimal('0.0000')
    return (total * (Decimal('1.0000') - order_discount)).quantize(Decimal('0.01'))


def customer_order_card(order):
    currency = _company_currency_payload(order)
    total = customer_order_total_after_discount(order)

    return {
        'id': order.id,
        'doc_type': 'customer_order',
        'order_number': order.order_number,
        'created_at': order.created_at,
        'status': _status_payload(order.status),
        'total_amount': _money(total),
        'amount_company_currency': _money(total),
        'company_currency_code': currency['company_currency_code'],
        'company_currency_symbol': currency['company_currency_symbol'],
    }


def supplier_order_items_total_cny(order):
    total = Decimal('0.00')
    for item in order.items.select_related('product'):
        unit_price = item.unit_price_cny
        if unit_price is None:
            unit_price = item.product.purchase_price or Decimal('0.00')
        total += (item.quantity or Decimal('0.00')) * (unit_price or Decimal('0.00'))
    return total.quantize(Decimal('0.01'))


def supplier_order_card(order):
    currency = {
        'company_currency_code': order.company_currency_code or order.company.base_currency_code,
        'company_currency_symbol': order.company_currency_symbol or order.company.base_currency_symbol,
        'cny_to_local_rate': order.cny_to_local_rate,
    }
    if order.amount_cny is not None:
        total = order.amount_cny
    else:
        total = supplier_order_items_total_cny(order)
    total_local = total * currency['cny_to_local_rate']

    return {
        'id': order.id,
        'doc_type': 'supplier_order',
        'order_number': order.order_number,
        'created_at': order.created_at,
        'status': _status_payload(order.status),
        'total_amount': _money(total),
        'amount_original': _money(total),
        'currency_original': 'CNY',
        'currency_original_symbol': '¥',
        'amount_company_currency': _money(total_local),
        'company_currency_code': currency['company_currency_code'],
        'company_currency_symbol': currency['company_currency_symbol'],
        'supplier_name': order.supplier.name if order.supplier else '',
    }


def build_customer_order_related_documents(customer_order):
    children = (
        customer_order.supplier_orders
        .select_related('supplier', 'status')
        .prefetch_related('items__product')
        .order_by('created_at', 'id')
    )
    return {
        'root': customer_order_card(customer_order),
        'children': [supplier_order_card(order) for order in children],
    }


def build_supplier_order_related_documents(supplier_order):
    if not supplier_order.customer_order_id:
        return {
            'root': None,
            'children': [supplier_order_card(supplier_order)],
        }

    supplier_orders = (
        supplier_order.customer_order.supplier_orders
        .select_related('supplier', 'status')
        .prefetch_related('items__product')
        .order_by('created_at', 'id')
    )
    return {
        'root': customer_order_card(supplier_order.customer_order),
        'children': [supplier_order_card(order) for order in supplier_orders],
    }


def _merge_supplier_items(customer_items):
    grouped = {}
    for item in customer_items:
        product_id = item.product_id
        if product_id not in grouped:
            grouped[product_id] = {
                'product': item.product,
                'quantity': Decimal('0.00'),
                'unit': item.unit,
                'comments': [],
            }
        grouped[product_id]['quantity'] += item.quantity or Decimal('0.00')
        if not grouped[product_id]['unit'] and item.unit:
            grouped[product_id]['unit'] = item.unit
        if item.comment and item.comment not in grouped[product_id]['comments']:
            grouped[product_id]['comments'].append(item.comment)

    return [
        {
            'product': data['product'],
            'quantity': data['quantity'],
            'unit': data['unit'],
            'comment': '; '.join(data['comments']),
        }
        for data in grouped.values()
    ]


def create_supplier_orders_for_customer_order(customer_order, user):
    if customer_order.company_id != user.company_id:
        raise SupplierOrderCreationError('Order is not available for this company.', status_code=403)

    items = list(
        customer_order.items
        .select_related('product__supplier')
        .order_by('id')
    )
    if not items:
        raise SupplierOrderCreationError('Customer order has no positions.')

    default_status = SupplierOrderStatus.objects.filter(company=customer_order.company).order_by('id').first()
    if not default_status:
        raise SupplierOrderCreationError('Supplier order status is not configured.')

    grouped_items = defaultdict(list)
    for item in items:
        supplier_id = item.product.supplier_id
        if not supplier_id:
            raise SupplierOrderCreationError(
                f'Product "{item.product.name}" has no supplier configured.'
            )
        grouped_items[supplier_id].append(item)

    created_orders = []
    updated_orders = []
    with transaction.atomic():
        for supplier_id, supplier_items in grouped_items.items():
            supplier_order = (
                SupplierOrder.objects
                .select_for_update()
                .filter(customer_order=customer_order, supplier_id=supplier_id)
                .first()
            )
            merged_items = _merge_supplier_items(supplier_items)

            if supplier_order:
                existing_items = {
                    item.product_id: item
                    for item in supplier_order.items.select_for_update().all()
                }
                changed = False
                new_items = []
                for item_data in merged_items:
                    product_id = item_data['product'].id
                    existing_item = existing_items.get(product_id)
                    if existing_item:
                        if (
                            existing_item.quantity != item_data['quantity']
                            or existing_item.unit != item_data['unit']
                            or existing_item.comment != item_data['comment']
                        ):
                            existing_item.quantity = item_data['quantity']
                            existing_item.unit = item_data['unit']
                            existing_item.comment = item_data['comment']
                            existing_item.save(update_fields=['quantity', 'unit', 'comment'])
                            changed = True
                    else:
                        new_items.append(SupplierOrderItem(
                            order=supplier_order,
                            unit_price_cny=item_data['product'].purchase_price or Decimal('0.00'),
                            **item_data,
                        ))
                if new_items:
                    SupplierOrderItem.objects.bulk_create(new_items)
                    changed = True
                total_cny = supplier_order_items_total_cny(supplier_order)
                amount_changed = supplier_order.amount_cny != total_cny
                if amount_changed:
                    supplier_order.amount_cny = total_cny
                if changed:
                    supplier_order.updated_by = user
                    update_fields = ['updated_by']
                    if amount_changed:
                        update_fields.append('amount_cny')
                    supplier_order.save(update_fields=update_fields)
                    sync_supplier_order(supplier_order, user)
                    updated_orders.append(supplier_order)
                elif amount_changed:
                    supplier_order.updated_by = user
                    supplier_order.save(update_fields=['amount_cny', 'updated_by'])
                    updated_orders.append(supplier_order)
                continue

            supplier_order = SupplierOrder.objects.create(
                company=customer_order.company,
                supplier_id=supplier_id,
                customer=customer_order.customer,
                customer_order=customer_order,
                status=default_status,
                planned_receipt_date=customer_order.planned_receipt_date,
                shipment_date=customer_order.shipment_date,
                shipping_address=customer_order.shipping_address,
                shipping_code=customer_order.shipping_code,
                created_by=user,
                updated_by=user,
            )
            SupplierOrderItem.objects.bulk_create([
                SupplierOrderItem(
                    order=supplier_order,
                    unit_price_cny=item_data['product'].purchase_price or Decimal('0.00'),
                    **item_data,
                )
                for item_data in merged_items
            ])
            supplier_order.amount_cny = supplier_order_items_total_cny(supplier_order)
            supplier_order.save(update_fields=['amount_cny'])
            sync_supplier_order(supplier_order, user)
            created_orders.append(supplier_order)

    return {
        'created': created_orders,
        'updated': updated_orders,
    }
