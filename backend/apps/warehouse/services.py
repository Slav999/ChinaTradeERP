from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import StockAlert, StockMovement, WarehouseStock


SUPPLIER_RECEIVED_STATUS_NAMES = {'received'}
CUSTOMER_SHIPPED_STATUS_NAMES = {'shipped', 'completed'}
CANCELLED_STATUS_NAMES = {'cancelled'}


def _normalized_status_name(status):
    return (getattr(status, 'code', '') or getattr(status, 'name', '') or '').strip().lower()


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


def _linked_supplier_product_ids(order):
    from supplier_orders.models import SupplierOrderItem

    return set(
        SupplierOrderItem.objects.filter(
            order__customer_order=order,
        ).values_list('product_id', flat=True)
    )


def _movement_sums(product):
    totals = StockMovement.objects.filter(product=product).values('movement_type').annotate(total=Sum('quantity'))
    by_type = {row['movement_type']: row['total'] or Decimal('0.00') for row in totals}
    on_hand = (
        by_type.get(StockMovement.TYPE_PURCHASE_RECEIVED, Decimal('0.00')) -
        by_type.get(StockMovement.TYPE_CUSTOMER_SHIPPED, Decimal('0.00')) +
        by_type.get(StockMovement.TYPE_ADJUSTMENT, Decimal('0.00')) +
        by_type.get(StockMovement.TYPE_DEFECT_RELEASED, Decimal('0.00')) -
        by_type.get(StockMovement.TYPE_STOCK_WRITTEN_OFF, Decimal('0.00'))
    )
    defective = (
        by_type.get(StockMovement.TYPE_DEFECT_RECEIVED, Decimal('0.00')) -
        by_type.get(StockMovement.TYPE_DEFECT_RELEASED, Decimal('0.00')) -
        by_type.get(StockMovement.TYPE_DEFECT_WRITTEN_OFF, Decimal('0.00'))
    )
    reserved = by_type.get(StockMovement.TYPE_CUSTOMER_RESERVED, Decimal('0.00'))
    expected = by_type.get(StockMovement.TYPE_PURCHASE_EXPECTED, Decimal('0.00'))
    return on_hand, reserved, expected, defective


def recalculate_product_stock(product):
    stock, _ = WarehouseStock.objects.get_or_create(
        company=product.company,
        product=product,
    )
    on_hand, reserved, expected, defective = _movement_sums(product)
    stock.quantity_on_hand = on_hand
    stock.quantity_reserved = reserved
    stock.quantity_expected = expected
    stock.quantity_defective = max(defective, Decimal('0.00'))
    stock.save(update_fields=['quantity_on_hand', 'quantity_reserved', 'quantity_expected', 'quantity_defective', 'updated_at'])
    sync_critical_stock_alert(stock)
    return stock


def sync_critical_stock_alert(stock):
    product = stock.product
    active_alerts = StockAlert.objects.filter(
        company=stock.company,
        product=product,
        status=StockAlert.STATUS_CRITICAL,
        resolved_at__isnull=True,
    )
    if not product.is_stock_item or product.minimum_stock_level is None:
        active_alerts.update(resolved_at=timezone.now())
        return None

    from .stock_control import company_stock_settings, stock_control_item

    settings = company_stock_settings(stock.company)
    row = stock_control_item(stock, settings)
    if row['status'] not in {'out_of_stock', 'below_minimum'}:
        active_alerts.update(resolved_at=timezone.now())
        return None

    defaults = {
        'available_quantity': Decimal(row['quantity_available']),
        'minimum_stock_level': Decimal(row['minimum_stock_level']),
        'expected_quantity': Decimal(row['quantity_expected']),
        'recommended_order_quantity': (
            Decimal(row['recommended_order_quantity'])
            if row['recommended_order_quantity'] is not None else None
        ),
    }
    alert, created = StockAlert.objects.get_or_create(
        company=stock.company,
        product=product,
        status=StockAlert.STATUS_CRITICAL,
        resolved_at=None,
        defaults=defaults,
    )
    if not created:
        for field, value in defaults.items():
            setattr(alert, field, value)
        alert.save(update_fields=[*defaults.keys()])
    return alert


def sync_supplier_order(order, user=None):
    from supplier_orders.models import SupplierOrderItem

    movement_type = None if order.customer_order_id else _supplier_movement_type(order.status)
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
            received_quantity = item.quantity or Decimal('0.00')
            if movement_type == StockMovement.TYPE_PURCHASE_RECEIVED:
                received_quantity -= item.defective_quantity or Decimal('0.00')
            source_key = f'{source_type}:{source_id}:{item.id}:{movement_type}'
            desired_keys.add(source_key)
            StockMovement.objects.update_or_create(
                source_key=source_key,
                defaults={
                    'company': order.company,
                    'product': product,
                    'movement_type': movement_type,
                    'quantity': max(received_quantity, Decimal('0.00')),
                    'source_type': source_type,
                    'source_id': source_id,
                    'comment': f'Supplier order #{order.order_number}',
                    'created_by': user,
                },
            )
            defective_quantity = item.defective_quantity or Decimal('0.00')
            if movement_type == StockMovement.TYPE_PURCHASE_RECEIVED and defective_quantity > 0:
                defect_key = f'{source_type}:{source_id}:{item.id}:{StockMovement.TYPE_DEFECT_RECEIVED}'
                desired_keys.add(defect_key)
                StockMovement.objects.update_or_create(
                    source_key=defect_key,
                    defaults={
                        'company': order.company,
                        'product': product,
                        'movement_type': StockMovement.TYPE_DEFECT_RECEIVED,
                        'quantity': defective_quantity,
                        'source_type': source_type,
                        'source_id': source_id,
                        'comment': f'Defect from supplier order #{order.order_number}',
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
    linked_supplier_product_ids = _linked_supplier_product_ids(order)
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
            if product.id in linked_supplier_product_ids:
                continue
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
    StockAlert.objects.filter(
        product=product,
        resolved_at__isnull=True,
    ).update(resolved_at=timezone.now())
    StockMovement.objects.filter(product=product).delete()
    return None
