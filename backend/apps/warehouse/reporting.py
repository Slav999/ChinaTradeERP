import io
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from supplier_orders.models import SupplierOrder, SupplierOrderItem

from .models import StockMovement


REPORT_HEADERS = (
    'Order #',
    'SKU',
    'Product',
    'Supplier',
    'Category',
    'Order date',
    'Receipt date',
    'Warehouse status',
    'Quantity',
    'Unit',
    'Unit price, CNY',
    'Total, CNY',
    'CNY rate',
    'Total, local currency',
    'Currency',
)


def warehouse_report_rows(company, filters):
    orders = SupplierOrder.objects.filter(company=company)
    if filters.get('date_from'):
        orders = orders.filter(created_at__date__gte=filters['date_from'])
    if filters.get('date_to'):
        orders = orders.filter(created_at__date__lte=filters['date_to'])
    if filters.get('supplier'):
        orders = orders.filter(supplier_id=filters['supplier'])

    items = SupplierOrderItem.objects.filter(
        order__in=orders,
        product__is_stock_item=True,
        product__is_archived=False,
    ).select_related(
        'order',
        'order__supplier',
        'product',
        'product__category',
        'product__unit',
    )
    if filters.get('category'):
        items = items.filter(product__category_id=filters['category'])
    if filters.get('search'):
        items = items.filter(
            Q(product__sku__icontains=filters['search']) |
            Q(product__name__icontains=filters['search'])
        )

    items = list(items.order_by('-order__created_at', 'order__order_number', 'id'))
    if not items:
        return []

    movements = StockMovement.objects.filter(
        company=company,
        source_type='supplier_order',
        source_id__in={item.order_id for item in items},
        movement_type__in=(
            StockMovement.TYPE_PURCHASE_EXPECTED,
            StockMovement.TYPE_PURCHASE_RECEIVED,
        ),
    )
    movement_by_key = {movement.source_key: movement for movement in movements}

    rows = []
    for item in items:
        received_key = (
            f'supplier_order:{item.order_id}:{item.id}:'
            f'{StockMovement.TYPE_PURCHASE_RECEIVED}'
        )
        expected_key = (
            f'supplier_order:{item.order_id}:{item.id}:'
            f'{StockMovement.TYPE_PURCHASE_EXPECTED}'
        )
        movement = movement_by_key.get(received_key) or movement_by_key.get(expected_key)
        if not movement:
            continue

        order = item.order
        product = item.product
        quantity = item.quantity or Decimal('0.00')
        unit_price = item.unit_price_cny or Decimal('0.00')
        total_cny = quantity * unit_price
        rate = order.cny_to_local_rate or Decimal('1.00')
        is_received = movement.movement_type == StockMovement.TYPE_PURCHASE_RECEIVED
        receipt_date = None
        if is_received:
            receipt_date = timezone.localtime(movement.created_at).replace(tzinfo=None)

        rows.append({
            'order_number': order.order_number,
            'sku': product.sku,
            'product_name': product.name,
            'supplier_name': order.supplier.name,
            'category_name': product.category.name if product.category else '',
            'order_date': timezone.localtime(order.created_at).replace(tzinfo=None),
            'receipt_date': receipt_date,
            'warehouse_status': 'Received' if is_received else 'Expected',
            'quantity': quantity,
            'unit': item.unit or (product.unit.name if product.unit else ''),
            'unit_price_cny': unit_price,
            'total_cny': total_cny,
            'cny_to_local_rate': rate,
            'total_local': total_cny * rate,
            'currency_code': order.company_currency_code or company.base_currency_code,
        })
    return rows


def build_warehouse_report_workbook(company, filters):
    rows = warehouse_report_rows(company, filters)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Warehouse report'
    sheet.append(REPORT_HEADERS)

    for row in rows:
        excel_row = sheet.max_row + 1
        sheet.append((
            row['order_number'],
            row['sku'],
            row['product_name'],
            row['supplier_name'],
            row['category_name'],
            row['order_date'],
            row['receipt_date'],
            row['warehouse_status'],
            float(row['quantity']),
            row['unit'],
            float(row['unit_price_cny']),
            None,
            float(row['cny_to_local_rate']),
            None,
            row['currency_code'],
        ))
        sheet.cell(excel_row, 12).value = f'=I{excel_row}*K{excel_row}'
        sheet.cell(excel_row, 14).value = f'=L{excel_row}*M{excel_row}'

    header_fill = PatternFill('solid', fgColor='2E465D')
    header_font = Font(color='FFFFFF', bold=True)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    sheet.row_dimensions[1].height = 24

    widths = (14, 16, 28, 24, 20, 18, 18, 18, 12, 12, 17, 17, 14, 22, 12)
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    for row_index in range(2, sheet.max_row + 1):
        sheet.cell(row_index, 6).number_format = 'dd.mm.yyyy hh:mm'
        sheet.cell(row_index, 7).number_format = 'dd.mm.yyyy hh:mm'
        sheet.cell(row_index, 9).number_format = '#,##0.00'
        for column_index in (11, 12, 13, 14):
            sheet.cell(row_index, column_index).number_format = '#,##0.00'

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer
