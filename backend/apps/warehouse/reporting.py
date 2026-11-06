import io
from collections import defaultdict
from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from counterparties.models import Counterparty
from core.order_reports import append_values, finish_sheet, localize_workbook, style_totals
from products.models import ProductCategory
from supplier_orders.models import SupplierOrder, SupplierOrderItem

from .models import StockMovement, WarehouseStock


def build_write_off_workbook(company, movements, period):
    ru = company.language_code != 'en'
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Списания' if ru else 'Write-offs'
    append_values(sheet, ['Отчёт по списаниям' if ru else 'Write-off report'])
    append_values(sheet, [('Компания: ' if ru else 'Company: ') + company.name, ('Период: ' if ru else 'Period: ') + period])
    append_values(sheet, [])
    append_values(sheet, ['Дата', 'Артикул', 'Товар', 'Количество', 'Единица', 'Причина / комментарий', 'Сотрудник'] if ru else
                  ['Date', 'SKU', 'Product', 'Quantity', 'Unit', 'Reason / comment', 'Employee'])
    totals = defaultdict(Decimal)
    reasons = {'marketing': 'Маркетинг и внутреннее использование', 'storage_damage': 'Повреждение при хранении',
               'inventory_adjustment': 'Корректировка после инвентаризации', 'other': 'Другое', 'defect': 'Брак'}
    for movement in movements:
        unit = movement.product.unit.name if movement.product.unit else '—'
        details = movement.comment or ''
        reason, separator, comment = details.partition(' · ')
        if ru:
            details = reasons.get(reason, reason) + (separator + comment if separator else '')
        if movement.movement_type == StockMovement.TYPE_DEFECT_WRITTEN_OFF:
            details = ('Непригодный брак' if ru else 'Unusable defect') + (f' · {details}' if details else '')
        employee = movement.created_by
        append_values(sheet, [movement.created_at, movement.product.sku, movement.product.name, movement.quantity,
                              unit, details, (employee.get_full_name() or employee.username) if employee else '—'])
        totals[unit] += movement.quantity
    last = sheet.max_row
    if last == 4:
        append_values(sheet, ['За выбранный период списаний нет' if ru else 'No write-offs for the selected period'])
    append_values(sheet, [])
    for unit, quantity in sorted(totals.items()):
        append_values(sheet, ['Итого' if ru else 'Total', '', '', quantity, unit])
    finish_sheet(sheet, 4, last)
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    sheet.column_dimensions['C'].width = 34
    sheet.column_dimensions['F'].width = 38
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


REPORT_OPERATIONAL_HEADERS = (
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
)

REPORT_FINANCIAL_HEADERS = (
    'Unit price, CNY',
    'Total, CNY',
    'CNY rate',
    'Total, local currency',
    'Currency',
)


SUMMARY_METRICS = {
    'quantity',
    'total_cny',
    'total_local',
}


def _warehouse_filters_text(company, filters):
    values = []
    if filters.get('date_from') or filters.get('date_to'):
        values.append(
            f'Order dates: {filters.get("date_from") or "All time"} — '
            f'{filters.get("date_to") or "Today"}'
        )
    if filters.get('search'):
        values.append(f'Search: {filters["search"]}')
    supplier = filters.get('supplier_query')
    if not supplier and filters.get('supplier'):
        supplier = Counterparty.objects.filter(
            company=company, pk=filters['supplier'], is_supplier=True,
        ).values_list('name', flat=True).first() or str(filters['supplier'])
    if supplier:
        values.append(f'Supplier: {supplier}')
    category = filters.get('category_query')
    if not category and filters.get('category'):
        category = ProductCategory.objects.filter(
            company=company, pk=filters['category'],
        ).values_list('name', flat=True).first() or str(filters['category'])
    if category:
        values.append(f'Category: {category}')
    if filters.get('only_available'):
        values.append('Only available: Yes')
    if filters.get('product_ids'):
        values.append(f'Selected products: {len(filters["product_ids"])}')
    return '; '.join(values) if values else 'None'


def warehouse_report_rows(company, filters):
    orders = SupplierOrder.objects.filter(company=company)
    if filters.get('date_from'):
        orders = orders.filter(created_at__date__gte=filters['date_from'])
    if filters.get('date_to'):
        orders = orders.filter(created_at__date__lte=filters['date_to'])
    if filters.get('supplier'):
        orders = orders.filter(supplier_id=filters['supplier'])
    if filters.get('supplier_query'):
        orders = orders.filter(supplier__name__icontains=filters['supplier_query'])

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
    if filters.get('category_query'):
        items = items.filter(product__category__name__icontains=filters['category_query'])
    if filters.get('search'):
        items = items.filter(
            Q(product__sku__icontains=filters['search']) |
            Q(product__name__icontains=filters['search'])
        )
    if filters.get('product_ids'):
        items = items.filter(product_id__in=filters['product_ids'])
    if filters.get('only_available'):
        available_product_ids = WarehouseStock.objects.filter(
            company=company,
            product__is_stock_item=True,
            product__is_archived=False,
            quantity_on_hand__gt=F('quantity_reserved'),
        ).values('product_id')
        items = items.filter(product_id__in=available_product_ids)

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
            'order_id': order.id,
            'product_id': product.id,
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


def warehouse_summary_rows(company, filters, *, include_financial=True):
    metric = filters.get('metric') or 'quantity'
    if metric not in SUMMARY_METRICS:
        metric = 'quantity'
    if not include_financial:
        metric = 'quantity'

    grouped = {}
    for row in warehouse_report_rows(company, filters):
        key = row['product_id']
        if key not in grouped:
            grouped[key] = {
                'product_id': row.get('product_id'),
                'sku': row['sku'],
                'product_name': row['product_name'],
                'supplier_name': row['supplier_name'],
                'category_name': row['category_name'],
                'quantity': Decimal('0.00'),
                'total_cny': Decimal('0.00'),
                'total_local': Decimal('0.00'),
                'unit': row['unit'],
                'currency_code': row['currency_code'],
                'breakdown': {
                    status: {metric: Decimal('0.00') for metric in SUMMARY_METRICS}
                    for status in ('received', 'expected')
                },
            }
        grouped[key]['quantity'] += row['quantity']
        grouped[key]['total_cny'] += row['total_cny']
        grouped[key]['total_local'] += row['total_local']
        status = 'received' if row['warehouse_status'] == 'Received' else 'expected'
        for metric_name in SUMMARY_METRICS:
            grouped[key]['breakdown'][status][metric_name] += row[metric_name]

    summary = list(grouped.values())
    quantities_by_unit = defaultdict(lambda: Decimal('0.00'))
    for item in summary:
        quantities_by_unit[item['unit']] += item['quantity']
    available_units = sorted(quantities_by_unit)
    selected_unit = None
    candidates = summary
    if metric == 'quantity' and available_units:
        requested_unit = filters.get('unit')
        selected_unit = requested_unit if requested_unit in quantities_by_unit else available_units[0]
        candidates = [item for item in summary if item['unit'] == selected_unit]
    candidates.sort(key=lambda item: item[metric], reverse=True)
    limited_summary = candidates[:20]

    result = {
        'metric': metric,
        'limit': 20,
        'available_units': available_units,
        'selected_unit': selected_unit,
        'items': [
            {
                **item,
                'breakdown': {
                    status: {
                        metric_name: str(value.quantize(Decimal('0.01')))
                        for metric_name, value in values.items()
                    }
                    for status, values in item['breakdown'].items()
                },
                'quantity': str(item['quantity'].quantize(Decimal('0.01'))),
                'total_cny': str(item['total_cny'].quantize(Decimal('0.01'))),
                'total_local': str(item['total_local'].quantize(Decimal('0.01'))),
            }
            for item in limited_summary
        ],
        'totals': {
            'quantity': (
                str(next(iter(quantities_by_unit.values())).quantize(Decimal('0.01')))
                if len(quantities_by_unit) == 1 else None
            ),
            'quantity_totals': [
                {
                    'unit': unit,
                    'quantity': str(quantity.quantize(Decimal('0.01'))),
                }
                for unit, quantity in sorted(quantities_by_unit.items())
            ],
            'total_cny': str(sum((item['total_cny'] for item in summary), Decimal('0.00')).quantize(Decimal('0.01'))),
            'total_local': str(sum((item['total_local'] for item in summary), Decimal('0.00')).quantize(Decimal('0.01'))),
            'products_count': len(candidates),
            'all_products_count': len(summary),
            'currency_code': company.base_currency_code,
        },
    }
    if not include_financial:
        for item in result['items']:
            item.pop('total_cny', None)
            item.pop('total_local', None)
            for values in item['breakdown'].values():
                values.pop('total_cny', None)
                values.pop('total_local', None)
        result['totals'].pop('total_cny', None)
        result['totals'].pop('total_local', None)
        result['totals'].pop('currency_code', None)
    return result


def build_warehouse_report_workbook(company, filters, *, include_financial=True):
    rows = warehouse_report_rows(company, filters)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Warehouse report'
    append_values(sheet, ['Warehouse report export'])
    append_values(sheet, ['Generated at', timezone.now()])
    append_values(sheet, ['Active filters', _warehouse_filters_text(company, filters)])
    order_ids = {row['order_id'] for row in rows}
    append_values(sheet, ['Exported', f'{len(order_ids)} orders; {len(rows)} positions; all matching pages'])
    append_values(sheet, [])
    headers = REPORT_OPERATIONAL_HEADERS + (REPORT_FINANCIAL_HEADERS if include_financial else ())
    append_values(sheet, headers)
    header_row = sheet.max_row

    order_keys = []
    for row in rows:
        excel_row = sheet.max_row + 1
        values = (
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
        )
        if include_financial:
            values += (
                float(row['unit_price_cny']),
                None,
                float(row['cny_to_local_rate']),
                None,
                row['currency_code'],
            )
        append_values(sheet, values)
        order_keys.append(row['order_id'])
        if include_financial:
            sheet.cell(excel_row, 12).value = f'=I{excel_row}*K{excel_row}'
            sheet.cell(excel_row, 14).value = f'=L{excel_row}*M{excel_row}'

    last_data_row = sheet.max_row
    append_values(sheet, [])
    append_values(sheet, ['Totals'])
    totals_title_row = sheet.max_row
    append_values(sheet, ['Orders count', len(order_ids)])
    append_values(sheet, ['Positions count', len(rows)])
    quantities_by_unit = defaultdict(lambda: Decimal('0.00'))
    for row in rows:
        quantities_by_unit[row['unit']] += row['quantity']
    for unit, quantity in sorted(quantities_by_unit.items()):
        append_values(sheet, [f'Total quantity, {unit or "unspecified unit"}', quantity])
    if rows and include_financial:
        append_values(sheet, ['Total, CNY', sum((row['total_cny'] for row in rows), Decimal('0.00'))])
        totals_by_currency = defaultdict(lambda: Decimal('0.00'))
        for row in rows:
            totals_by_currency[row['currency_code']] += row['total_local']
        for currency, amount in sorted(totals_by_currency.items()):
            append_values(sheet, [f'Total, {currency}', amount])

    for row_index in range(header_row + 1, last_data_row + 1):
        sheet.cell(row_index, 6).number_format = 'dd.mm.yyyy hh:mm'
        sheet.cell(row_index, 7).number_format = 'dd.mm.yyyy hh:mm'
        sheet.cell(row_index, 9).number_format = '#,##0.00'
        if include_financial:
            for column_index in (11, 12, 13, 14):
                sheet.cell(row_index, column_index).number_format = '#,##0.00'

    finish_sheet(sheet, header_row, last_data_row, order_keys)
    style_totals(sheet, totals_title_row, sheet.max_row)
    localize_workbook(workbook, company)

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


STOCK_CONTROL_HEADERS = (
    'Status',
    'SKU',
    'Product',
    'Supplier',
    'Unit',
    'On hand',
    'Defective',
    'Physical stock',
    'Reserved',
    'Available',
    'Minimum stock',
    'Expected',
    'Average monthly consumption',
    'Consumption source',
    'Forecast quality',
    'Observed days',
    'Purchase batch',
    'Delivery lead, days',
    'Consumption during lead',
    'Projected stock',
    'Deficit at delivery',
    'Recommended order',
)


def build_stock_control_workbook(snapshot):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Stock control'
    summary = snapshot.summary
    append_values(sheet, ['Warehouse stock control'])
    append_values(sheet, ['Generated at', snapshot.generated_at])
    append_values(sheet, [
        'Parameters',
        f'Delivery lead: {snapshot.delivery_lead_days} days; time zone: {snapshot.timezone_name}',
    ])
    append_values(sheet, [
        'Summary',
        f'{summary.get("attention_count", 0)} require attention; '
        f'{summary.get("out_of_stock_count", 0)} out of stock; '
        f'{summary.get("below_minimum_count", summary.get("critical_count", 0))} below minimum; '
        f'{summary.get("requires_order_count", 0)} require order; '
        f'{summary.get("supply_expected_count", 0)} covered by incoming supply; '
        f'{summary.get("no_forecast_count", 0)} without forecast data',
    ])
    append_values(sheet, [])
    append_values(sheet, STOCK_CONTROL_HEADERS)
    header_row = sheet.max_row
    order_keys = []
    status_rows = []
    for item in snapshot.items:
        append_values(sheet, (
            item['status_label'],
            item['sku'],
            item['product_name'],
            item['supplier_name'],
            item['unit'],
            Decimal(item['quantity_on_hand']),
            Decimal(item.get('quantity_defective', '0.00')),
            Decimal(item.get('quantity_physical', item['quantity_on_hand'])),
            Decimal(item['quantity_reserved']),
            Decimal(item['quantity_available']),
            Decimal(item['minimum_stock_level']),
            Decimal(item['quantity_expected']),
            Decimal(item['average_monthly_consumption']) if item.get('average_monthly_consumption') is not None else None,
            (item.get('consumption_source') or '').title(),
            item.get('forecast_quality_label') or (item.get('consumption_confidence') or '').replace('_', ' ').title(),
            item.get('consumption_observed_days'),
            Decimal(item['purchase_batch_size']) if item.get('purchase_batch_size') is not None else None,
            item['delivery_lead_days'],
            Decimal(item['consumption_during_lead']) if item.get('consumption_during_lead') is not None else None,
            Decimal(item['projected_stock']) if item.get('projected_stock') is not None else None,
            Decimal(item['shortage_at_delivery']) if item.get('shortage_at_delivery') is not None else None,
            Decimal(item['recommended_order_quantity']) if item.get('recommended_order_quantity') is not None else None,
        ))
        order_keys.append(item['product_id'])
        status_rows.append((sheet.max_row, item['status']))

    last_data_row = sheet.max_row
    append_values(sheet, [])
    append_values(sheet, ['Totals'])
    totals_title_row = sheet.max_row
    append_values(sheet, ['Monitored products', summary.get('total_count', 0)])
    append_values(sheet, ['Require attention', summary.get('attention_count', 0)])
    append_values(sheet, ['Out of stock', summary.get('out_of_stock_count', 0)])
    append_values(sheet, ['Below minimum', summary.get('below_minimum_count', summary.get('critical_count', 0))])
    append_values(sheet, ['Order required', summary.get('requires_order_count', 0)])
    append_values(sheet, ['Incoming supply covers demand', summary.get('supply_expected_count', 0)])
    append_values(sheet, ['No forecast data', summary.get('no_forecast_count', 0)])
    append_values(sheet, ['Normal', summary.get('normal_count', 0)])

    finish_sheet(sheet, header_row, last_data_row, order_keys)
    style_totals(sheet, totals_title_row, sheet.max_row)
    status_styles = {
        'out_of_stock': ('F8D7DA', '842029'),
        'below_minimum': ('F8D7DA', '842029'),
        'critical': ('F8D7DA', '842029'),
        'requires_order': ('FFF3CD', '664D03'),
        'supply_expected': ('CFF4FC', '055160'),
        'no_forecast': ('E2E3E5', '41464B'),
        'normal': ('D1E7DD', '0F5132'),
    }
    for row_number, status in status_rows:
        fill, color = status_styles[status]
        cell = sheet.cell(row_number, 1)
        cell.fill = PatternFill('solid', fgColor=fill)
        cell.font = Font(bold=True, color=color)
        for column_number in range(6, 21):
            sheet.cell(row_number, column_number).number_format = '#,##0.00'

    company = getattr(snapshot, 'company', None)
    if company is not None:
        localize_workbook(workbook, company)

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer
