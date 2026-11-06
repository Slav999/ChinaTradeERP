"""Owner-facing analytics, independent of the order-list search and status."""
from collections import defaultdict
from decimal import Decimal
from io import BytesIO

from django.http import FileResponse
from django.db.models import Q
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, TwoCellAnchor
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.views import Selection
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from counterparties.models import Counterparty
from warehouse.services import CANCELLED_STATUS_NAMES
from .order_reports import ZERO, money, append_values, finish_sheet, localize_workbook, translate_report_text


class AnalyticsFilters(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    counterparty = serializers.IntegerField(required=False, min_value=1)
    ranking_limit = serializers.CharField(required=False, default='10', max_length=3)

    def validate(self, attrs):
        if attrs.get('date_from') and attrs.get('date_to') and attrs['date_from'] > attrs['date_to']:
            raise ValidationError('End date must be on or after start date.')
        return attrs


def quantities_text(quantities):
    return '; '.join(f'{value:,.2f} {unit or "unspecified unit"}' for unit, value in sorted(quantities.items()))


def defect_rates_text(quantities, defects):
    values = []
    for unit, defective in sorted(defects.items()):
        quantity = quantities.get(unit, ZERO)
        rate = defective / quantity * 100 if quantity else ZERO
        values.append(f'{rate:.2f}% {unit or "unspecified unit"}')
    return '; '.join(values)


def reserve_blank_rows(sheet, count, height=15):
    """Create real blank spreadsheet rows that Excel cannot collapse."""
    for _ in range(count):
        row_number = sheet.max_row + 1
        sheet.cell(row=row_number, column=1, value='')
        sheet.row_dimensions[row_number].height = height


SECTION_GAP_ROWS = 2
SECTION_GAP_HEIGHT = 20


def add_amount_chart(
    sheet, kind, selected, company, header, last, top_header, top_last,
    anchor_row, end_row,
):
    supplier = kind == 'supplier'
    if selected:
        first_row = top_header + 1
        last_row = min(top_last, top_header + 5)
        category_column = 4
        value_column = 10 if supplier else 9
        title = 'Purchase amounts for listed top products' if supplier else 'Sales amounts for listed top products'
    else:
        first_row = header + 1
        last_row = min(last, header + 10)
        category_column = 2
        value_column = 5
        title = 'Top 10 suppliers by purchase amount' if supplier else 'Top 10 customers by sales amount'
    if last_row < first_row:
        return

    currency = 'CNY' if supplier else company.base_currency_code
    chart = BarChart()
    chart.type = 'bar'
    chart.style = 10
    chart.title = translate_report_text(f'{title}, {currency}', company)
    chart.title.overlay = False
    chart.legend = None
    chart.gapWidth = 85
    chart.x_axis.scaling.orientation = 'maxMin'
    chart.x_axis.tickLblPos = 'nextTo'
    chart.y_axis.tickLblPos = 'nextTo'
    chart.x_axis.majorGridlines = None
    chart.y_axis.majorGridlines = None
    chart.dLbls = DataLabelList()
    chart.dLbls.showVal = True
    chart.dLbls.showSerName = False
    chart.dLbls.showCatName = False
    chart.dLbls.showLegendKey = False
    chart.dLbls.showPercent = False
    chart.dLbls.showBubbleSize = False
    chart.dLbls.showLeaderLines = False
    chart.dLbls.dLblPos = 'outEnd'
    chart.dLbls.numFmt = '#,##0.00'
    amounts = [sheet.cell(row, value_column).value or ZERO for row in range(first_row, last_row + 1)]
    largest_amount = max(amounts, default=ZERO)
    chart.y_axis.scaling.min = 0
    if largest_amount > 0:
        chart.y_axis.scaling.max = float(largest_amount * Decimal('1.18'))
    chart.add_data(
        Reference(sheet, min_col=value_column, min_row=first_row, max_row=last_row),
        titles_from_data=False,
    )
    chart.set_categories(
        Reference(sheet, min_col=category_column, min_row=first_row, max_row=last_row)
    )
    chart.series[0].graphicalProperties.solidFill = '4F81BD'
    chart.series[0].graphicalProperties.line.solidFill = '385D8A'
    chart.anchor = TwoCellAnchor(
        editAs='twoCell',
        _from=AnchorMarker(col=0, row=anchor_row - 1),
        to=AnchorMarker(col=12 if supplier else 10, row=end_row),
    )
    sheet.add_chart(chart)


def analytics_response(request, model, kind):
    validator = AnalyticsFilters(data=request.query_params)
    validator.is_valid(raise_exception=True)
    filters = validator.validated_data
    company = request.user.company
    role = 'supplier' if kind == 'supplier' else 'customer'
    allowed_limits = {'10', 'all'} if kind == 'supplier' else {'10', '20', '30', 'all'}
    if filters['ranking_limit'] not in allowed_limits:
        raise ValidationError({'ranking_limit': 'Unsupported ranking size.'})
    selected = None
    if filters.get('counterparty'):
        selected = Counterparty.objects.filter(company=company, pk=filters['counterparty'], **{f'is_{role}': True}).first()
        if selected is None:
            raise ValidationError({'counterparty': 'Counterparty is not available.'})
    orders = model.objects.filter(company=company)
    if kind == 'supplier':
        orders = orders.filter(is_sample=False)
    if selected:
        orders = orders.filter(**{role: selected})
    if filters.get('date_from'):
        orders = orders.filter(created_at__date__gte=filters['date_from'])
    if filters.get('date_to'):
        orders = orders.filter(created_at__date__lte=filters['date_to'])
    cancelled_filter = Q(status__code='cancelled')
    for name in CANCELLED_STATUS_NAMES:
        cancelled_filter |= Q(status__name__iexact=name)
    orders = orders.exclude(cancelled_filter)
    buffer = build_analytics(orders, company, kind, filters, selected)
    return FileResponse(buffer, as_attachment=True, filename=f'{kind}_analytics.xlsx',
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def build_analytics(orders, company, kind, filters, selected=None):
    supplier = kind == 'supplier'
    role = 'supplier' if supplier else 'customer'
    groups = {}
    all_qty = defaultdict(lambda: ZERO)
    for order in orders.select_related(role).prefetch_related('items__product__unit', 'items__product__supplier'):
        party = getattr(order, role)
        currency = (order.company_currency_code or company.base_currency_code) if supplier else company.base_currency_code
        # Currency is part of the group: historical currencies must never be added together.
        key = (getattr(party, 'pk', None), currency)
        group = groups.setdefault(key, {'name': party.name if party else 'Not specified', 'currency': currency,
                                       'count': 0, 'qty': defaultdict(lambda: ZERO),
                                       'defective': defaultdict(lambda: ZERO),
                                       'cny': ZERO, 'local': ZERO, 'products': {}})
        group['count'] += 1
        subtotal = ZERO
        for item in order.items.all():
            product = item.product
            quantity = item.quantity or ZERO
            defective = (item.defective_quantity or ZERO) if supplier else ZERO
            unit = item.unit or (product.unit.name if product.unit else '')
            group['qty'][unit] += quantity
            group['defective'][unit] += defective
            all_qty[unit] += quantity
            entry = group['products'].setdefault((product.pk, unit), {
                'sku': product.sku, 'name': product.name, 'factory': product.supplier.name if product.supplier else '',
                'orders': set(), 'quantity': ZERO, 'defective': ZERO, 'unit': unit, 'cny': ZERO, 'local': ZERO,
            })
            entry['orders'].add(order.pk)
            entry['quantity'] += quantity
            entry['defective'] += defective
            if supplier:
                price = item.unit_price_cny if item.unit_price_cny is not None else product.purchase_price
                amount = quantity * (price or ZERO)
                entry['cny'] += money(amount)
                entry['local'] += money(amount * order.cny_to_local_rate)
            else:
                price = item.unit_sale_price if item.unit_sale_price is not None else product.sale_price
                amount = quantity * (price or ZERO) * (Decimal('1') - (item.discount_pct or ZERO))
                entry['local'] += money(amount * (Decimal('1') - (order.discount_pct or ZERO)))
            subtotal += amount
        if supplier:
            amount = order.amount_cny if order.amount_cny is not None else money(subtotal)
            group['cny'] += amount
            group['local'] += money(amount * order.cny_to_local_rate)
        else:
            group['local'] += money(money(subtotal) * (Decimal('1') - (order.discount_pct or ZERO)))

    ranked_all = sorted(groups.values(), key=lambda g: (-g['cny'], g['name']) if supplier else
                    (g['currency'], -g['local'], -g['count'], g['name']))
    currency_totals = defaultdict(lambda: ZERO)
    for group in ranked_all:
        currency_totals[group['currency']] += group['local']
    total_cny = sum((g['cny'] for g in ranked_all), ZERO)
    if selected or filters['ranking_limit'] == 'all':
        ranked = ranked_all
    else:
        ranked = ranked_all[:int(filters['ranking_limit'])]
    workbook = Workbook()
    sheet = workbook.active
    # Set the final localized sheet name before chart references are created.
    # Renaming it afterwards leaves Excel charts pointing at a missing sheet.
    sheet.title = translate_report_text('Analytics', company)
    report_columns = 12 if supplier else 10
    append_values(sheet, [f'{role.title()} report'])
    title_row = sheet.max_row
    period = f'{filters.get("date_from", "All time")} — {filters.get("date_to", "Today")}'
    append_values(sheet, ['Order dates', period])
    append_values(sheet, [role.title(), selected.name if selected else 'All'])
    append_values(sheet, ['Generated at', timezone.now()])
    scope = 'All counterparties' if selected or filters['ranking_limit'] == 'all' else f'Top {filters["ranking_limit"]} counterparties'
    append_values(sheet, ['Scope', f'{scope}; cancelled orders excluded; list search and status ignored'])
    append_values(sheet, ['Orders', sum(g['count'] for g in ranked_all), 'Counterparties', len({key[0] for key in groups})])
    append_values(sheet, ['Quantity', quantities_text(all_qty)])
    if supplier:
        append_values(sheet, ['Total, CNY', total_cny])
    for currency, amount in sorted(currency_totals.items()):
        append_values(sheet, [f'Total, {currency}', amount])
    summary_end = sheet.max_row
    chart_item_count = (
        min(5, sum(len(group['products']) for group in ranked))
        if selected else min(10, len(ranked))
    )
    has_chart_data = chart_item_count > 0
    chart_row_count = max(10, min(18, 8 + chart_item_count))
    reserve_blank_rows(sheet, SECTION_GAP_ROWS, height=SECTION_GAP_HEIGHT)
    chart_anchor_row = None
    chart_end_row = None
    if has_chart_data:
        chart_anchor_row = sheet.max_row + 1
        reserve_blank_rows(sheet, chart_row_count)
        chart_end_row = sheet.max_row
        reserve_blank_rows(sheet, SECTION_GAP_ROWS, height=SECTION_GAP_HEIGHT)
    headers = ['Rank', role.title(), 'Orders', 'Quantity by unit']
    headers += ['Total, CNY', 'Total, local', 'Currency', 'Purchase share, %', 'Defective quantity', 'Defect rate by unit'] if supplier else [
        'Total, local', 'Currency', 'Sales share, %', 'Average order']
    append_values(sheet, headers)
    header = sheet.max_row
    for rank, group in enumerate(ranked, 1):
        row = [rank, group['name'], group['count'], quantities_text(group['qty'])]
        if supplier:
            share = group['cny'] / total_cny * 100 if total_cny else ZERO
            row += [group['cny'], group['local'], group['currency'], money(share),
                    quantities_text(group['defective']), defect_rates_text(group['qty'], group['defective'])]
        else:
            total = currency_totals[group['currency']]
            row += [group['local'], group['currency'], money(group['local'] / total * 100) if total else ZERO,
                    money(group['local'] / group['count'])]
        append_values(sheet, row)
    last = sheet.max_row
    reserve_blank_rows(sheet, SECTION_GAP_ROWS, height=SECTION_GAP_HEIGHT)
    append_values(sheet, [f'Top 5 products per {role}'])
    products_title_row = sheet.max_row
    top_headers = ['Rank', role.title(), 'SKU', 'Product'] + ([] if supplier else ['Product supplier'])
    top_headers += ['Orders', 'Quantity', 'Unit']
    if supplier:
        top_headers += ['Defective quantity', 'Defect rate, %', 'Total, CNY']
    top_headers += ['Total, local', 'Currency']
    append_values(sheet, top_headers)
    top_header = sheet.max_row
    for group in ranked:
        products = sorted(group['products'].values(), key=lambda p: (-len(p['orders']), -p['local'], p['sku'], p['unit']))[:5]
        for rank, item in enumerate(products, 1):
            row = [rank, group['name'], item['sku'], item['name']] + ([] if supplier else [item['factory']])
            row += [len(item['orders']), item['quantity'], item['unit']]
            if supplier:
                rate = item['defective'] / item['quantity'] * 100 if item['quantity'] else ZERO
                row += [item['defective'], money(rate), item['cny']]
            row += [item['local'], group['currency']]
            append_values(sheet, row)
    top_last = sheet.max_row
    if has_chart_data:
        add_amount_chart(
            sheet, kind, selected, company,
            header, last, top_header, top_last, chart_anchor_row, chart_end_row,
        )
    finish_sheet(sheet, top_header, sheet.max_row)
    finish_sheet(sheet, header, last)
    sheet.merge_cells(start_row=title_row, start_column=1, end_row=title_row, end_column=report_columns)
    for row_number in range(title_row + 1, summary_end + 1):
        if row_number == title_row + 5:
            sheet.merge_cells(start_row=row_number, start_column=4, end_row=row_number, end_column=report_columns)
        else:
            sheet.merge_cells(start_row=row_number, start_column=2, end_row=row_number, end_column=report_columns)
    sheet.merge_cells(
        start_row=products_title_row, start_column=1,
        end_row=products_title_row, end_column=report_columns,
    )
    # These reports are already ordered as a ranking. Excel filter drop-downs add
    # visual noise here and can misleadingly suggest that the file is interactive.
    sheet.auto_filter.ref = None
    sheet.freeze_panes = None
    # openpyxl removes the pane but leaves its old selections behind.
    sheet.sheet_view.selection = [Selection(activeCell='A1', sqref='A1')]
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    for header_row in (header, top_header):
        for cell in sheet[header_row]:
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    dark_fill = PatternFill('solid', fgColor='2E465D')
    light_fill = PatternFill('solid', fgColor='E8EEF4')
    value_fill = PatternFill('solid', fgColor='F8FAFC')
    border = Border(
        left=Side(style='thin', color='B8C4CE'),
        right=Side(style='thin', color='B8C4CE'),
        top=Side(style='thin', color='B8C4CE'),
        bottom=Side(style='thin', color='B8C4CE'),
    )
    for cell in sheet[title_row]:
        cell.fill = dark_fill
        cell.border = border
    sheet.cell(title_row, 1).font = Font(size=16, bold=True, color='FFFFFF')
    sheet.cell(title_row, 1).alignment = Alignment(horizontal='left', vertical='center')
    sheet.row_dimensions[title_row].height = 28
    for row_number in range(title_row + 1, summary_end + 1):
        sheet.row_dimensions[row_number].height = 34
        for cell in sheet[row_number][:report_columns]:
            cell.fill = value_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        for column in (1, 3):
            cell = sheet.cell(row_number, column)
            if cell.value is not None:
                cell.fill = light_fill
                cell.font = Font(bold=True, color='2E465D')
    sheet.row_dimensions[title_row + 4].height = 46
    for cell in sheet[products_title_row][:report_columns]:
        cell.border = border
        cell.fill = dark_fill
    sheet.cell(products_title_row, 1).font = Font(size=12, bold=True, color='FFFFFF')
    sheet.row_dimensions[products_title_row].height = 24
    widths = {
        'A': 12, 'B': 28, 'C': 16, 'D': 32, 'E': 20, 'F': 18,
        'G': 14, 'H': 20, 'I': 22, 'J': 22, 'K': 18, 'L': 14,
    }
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    buffer = BytesIO()
    localize_workbook(workbook, company)
    workbook.save(buffer)
    buffer.seek(0)
    return buffer
