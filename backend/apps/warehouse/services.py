from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import StockMovement, WarehouseStock


SUPPLIER_RECEIVED_STATUS_NAMES = {'received'}
CUSTOMER_SHIPPED_STATUS_NAMES = {'shipped', 'completed'}
CANCELLED_STATUS_NAMES = {'cancelled'}


def _normalized_status_name(status):
    return (getattr(status, 'name', '') or '').strip().lower()


def _supplier_movement_type(status):
    status_name = _normalized_status_name(status)
    if status_name in CANCELLED_STATUS_NAMES:
        return None
    if status_name in SUPPLIER_RECEIVED_STATUS_NAMES:
        return StockMovement.TYPE_PURCHASE_RECEIVED
    return StockMovement.TYPE_PURCHASE_EXPECTED


def _customer_movement_type(status):
    status_name = _normalized_status_name(status)
    if status_name in CANCELLED_STATUS_NAMES:
        return None
    if status_name in CUSTOMER_SHIPPED_STATUS_NAMES:
        return StockMovement.TYPE_CUSTOMER_SHIPPED
    return StockMovement.TYPE_CUSTOMER_RESERVED


def _movement_sums(product):
    totals = StockMovement.objects.filter(product=product).values('movement_type').annotate(total=Sum('quantity'))
    by_type = {row['movement_type']: row['total'] or Decimal('0.00') for row in totals}
    on_hand = (
        by_type.get(StockMovement.TYPE_PURCHASE_RECEIVED, Decimal('0.00')) -
        by_type.get(StockMovement.TYPE_CUSTOMER_SHIPPED, Decimal('0.00')) +
        by_type.get(StockMovement.TYPE_ADJUSTMENT, Decimal('0.00'))
    )
    reserved = by_type.get(StockMovement.TYPE_CUSTOMER_RESERVED, Decimal('0.00'))
    expected = by_type.get(StockMovement.TYPE_PURCHASE_EXPECTED, Decimal('0.00'))
    return on_hand, reserved, expected


def recalculate_product_stock(product):
    stock, _ = WarehouseStock.objects.get_or_create(
        company=product.company,
        product=product,
    )
    on_hand, reserved, expected = _movement_sums(product)
    stock.quantity_on_hand = on_hand
    stock.quantity_reserved = reserved
    stock.quantity_expected = expected
    stock.save(update_fields=['quantity_on_hand', 'quantity_reserved', 'quantity_expected', 'updated_at'])
    return stock


def sync_supplier_order(order, user=None):
    from supplier_orders.models import SupplierOrderItem

    movement_type = _supplier_movement_type(order.status)
    source_type = 'supplier_order'
    source_id = order.id
    touched_products = set(
        StockMovement.objects.filter(
            company=order.company,
            source_type=source_type,
            source_id=source_id,
        ).values_list('product_id', flat=True)
    )
    desired_keys = set()
    with transaction.atomic():
        items = SupplierOrderItem.objects.filter(order=order).select_related('product')
        for item in items:
            product = item.product
            if not product.is_stock_item:
                continue
            touched_products.add(product.id)
            if movement_type is None:
                continue
            source_key = f'{source_type}:{source_id}:{item.id}:{movement_type}'
            desired_keys.add(source_key)
            StockMovement.objects.update_or_create(
                source_key=source_key,
                defaults={
                    'company': order.company,
                    'product': product,
                    'movement_type': movement_type,
                    'quantity': item.quantity or Decimal('0.00'),
                    'source_type': source_type,
                    'source_id': source_id,
                    'comment': f'Supplier order #{order.order_number}',
                    'created_by': user,
                },
            )
        stale_movements = StockMovement.objects.filter(
            company=order.company,
            source_type=source_type,
            source_id=source_id,
        )
        if desired_keys:
            stale_movements = stale_movements.exclude(source_key__in=desired_keys)
        stale_movements.delete()
        for product_id in touched_products:
            product = order.company.products.get(id=product_id)
            recalculate_product_stock(product)


def sync_customer_order(order, user=None):
    from customer_orders.models import CustomerOrderItem

    movement_type = _customer_movement_type(order.status)
    source_type = 'customer_order'
    source_id = order.id
    touched_products = set(
        StockMovement.objects.filter(
            company=order.company,
            source_type=source_type,
            source_id=source_id,
        ).values_list('product_id', flat=True)
    )
    desired_keys = set()
    with transaction.atomic():
        items = CustomerOrderItem.objects.filter(order=order).select_related('product')
        for item in items:
            product = item.product
            if not product.is_stock_item:
                continue
            touched_products.add(product.id)
            if movement_type is None:
                continue
            source_key = f'{source_type}:{source_id}:{item.id}:{movement_type}'
            desired_keys.add(source_key)
            StockMovement.objects.update_or_create(
                source_key=source_key,
                defaults={
                    'company': order.company,
                    'product': product,
                    'movement_type': movement_type,
                    'quantity': item.quantity or Decimal('0.00'),
                    'source_type': source_type,
                    'source_id': source_id,
                    'comment': f'Customer order #{order.order_number}',
                    'created_by': user,
                },
            )
        stale_movements = StockMovement.objects.filter(
            company=order.company,
            source_type=source_type,
            source_id=source_id,
        )
        if desired_keys:
            stale_movements = stale_movements.exclude(source_key__in=desired_keys)
        stale_movements.delete()
        for product_id in touched_products:
            product = order.company.products.get(id=product_id)
            recalculate_product_stock(product)


def ensure_stock_for_product(product):
    if product.is_stock_item:
        for supplier_order in product.supplier_order_items.select_related('order', 'order__status').all():
            sync_supplier_order(supplier_order.order)
        for customer_order in product.customer_order_items.select_related('order', 'order__status').all():
            sync_customer_order(customer_order.order)
        return recalculate_product_stock(product)
    WarehouseStock.objects.filter(product=product).delete()
    StockMovement.objects.filter(product=product).delete()
    return None
