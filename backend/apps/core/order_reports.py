"""Filtered order exports; amounts follow the existing order API calculations."""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


ZERO = Decimal('0.00')

EXCEL_RU = {
    'Orders': 'Заказы', 'Analytics': 'Аналитика', 'Warehouse report': 'Отчёт склада',
    'Stock control': 'Контроль остатков', 'Generated at': 'Сформировано', 'Active filters': 'Активные фильтры',
    'Exported': 'Выгружено', 'Totals': 'Итоги', 'Orders count': 'Количество заказов',
    'Positions count': 'Количество позиций', 'Status': 'Статус', 'SKU': 'Артикул', 'Product': 'Товар',
    'Supplier': 'Поставщик', 'Customer': 'Покупатель', 'Category': 'Категория', 'Unit': 'Единица',
    'Order #': 'Заказ №', 'Year': 'Год', 'Created at': 'Создан', 'Track number': 'Трек-номер',
    'Product supplier': 'Поставщик товара', 'Quantity': 'Количество', 'Defective quantity': 'Количество брака',
    'Defect rate, %': 'Доля брака, %', 'Unit price, CNY': 'Цена за единицу, CNY', 'Total, CNY': 'Итого, CNY',
    'CNY rate': 'Курс CNY', 'Total, local': 'Итого в местной валюте', 'Currency': 'Валюта',
    'Unit price, local': 'Цена за единицу в местной валюте', 'Line discount, %': 'Скидка позиции, %',
    'Order discount, %': 'Скидка заказа, %', 'Warehouse report export': 'Отчёт склада',
    'Order date': 'Дата заказа', 'Receipt date': 'Дата поступления', 'Warehouse status': 'Статус склада',
    'Total, local currency': 'Итого в местной валюте', 'Warehouse stock control': 'Контроль складских остатков',
    'Parameters': 'Параметры', 'Summary': 'Сводка', 'On hand': 'Физический остаток', 'Reserved': 'В резерве',
    'Available': 'Доступно', 'Minimum stock': 'Минимальный остаток', 'Expected': 'Ожидается',
    'Average monthly consumption': 'Средний расход в месяц', 'Consumption source': 'Источник расхода',
    'Forecast quality': 'Качество прогноза', 'Observed days': 'Дней наблюдения', 'Purchase batch': 'Закупочная партия',
    'Delivery lead, days': 'Срок поставки, дней', 'Consumption during lead': 'Расход за срок поставки',
    'Projected stock': 'Прогнозный остаток', 'Deficit at delivery': 'Дефицит к поставке',
    'Recommended order': 'Рекомендуемый заказ', 'Monitored products': 'Контролируемые товары',
    'Require attention': 'Требуют внимания', 'Out of stock': 'Нет в наличии', 'Below minimum': 'Ниже минимума',
    'Order required': 'Требуется заказ', 'Incoming supply covers demand': 'Поставка покрывает потребность',
    'No forecast data': 'Нет данных для прогноза', 'Normal': 'Норма', 'Manual': 'Ручной',
    'Preliminary': 'Предварительный', 'Reliable': 'Надёжный', 'No data': 'Нет данных',
    'Received': 'Получено', 'Order dates': 'Даты заказов', 'Scope': 'Охват',
    'Counterparties': 'Контрагенты', 'All': 'Все', 'All time': 'За всё время', 'Today': 'Сегодня',
    'None': 'Нет', 'Yes': 'Да', 'Rank': 'Место', 'Orders': 'Заказы',
    'Quantity by unit': 'Количество по единицам', 'Purchase share, %': 'Доля закупок, %',
    'Defect rate by unit': 'Доля брака по единицам', 'Sales share, %': 'Доля продаж, %',
    'Average order': 'Средний чек', 'Not specified': 'Не указано',
    'All counterparties': 'Все контрагенты', 'Only available: Yes': 'Только в наличии: Да',
    'Purchase amounts for listed top products': 'Суммы закупок по указанным популярным товарам',
    'Sales amounts for listed top products': 'Суммы продаж по указанным популярным товарам',
    'Top 10 suppliers by purchase amount': 'Топ-10 поставщиков по сумме закупок',
    'Top 10 customers by sales amount': 'Топ-10 покупателей по сумме продаж',
    'Top 5 products per supplier': 'Топ-5 товаров по каждому поставщику',
    'Top 5 products per customer': 'Топ-5 товаров по каждому покупателю',
    'Automatic': 'Автоматический', 'New': 'Новый', 'Active': 'Активный',
    'Blocked': 'Заблокирован', 'In progress': 'В работе', 'Shipped': 'Отгружен',
    'Completed': 'Завершён', 'Cancelled': 'Отменён', 'In production': 'В производстве',
    'In transit': 'В пути',
}


def translate_report_text(value, company=None):
    if company is not None and getattr(company, 'language_code', 'ru') != 'ru':
        return value
    if not isinstance(value, str):
        return value
    if value in EXCEL_RU:
        return EXCEL_RU[value]
    for source, target in (
        ('Supplier orders export', 'Отчёт по заказам поставщикам'),
        ('Customer orders export', 'Отчёт по заказам покупателей'),
        ('Supplier report', 'Отчёт по поставщикам'),
        ('Customer report', 'Отчёт по покупателям'),
        ('Total quantity, ', 'Общее количество, '),
        ('Defective quantity, ', 'Количество брака, '),
        ('Search: ', 'Поиск: '), ('Supplier: ', 'Поставщик: '),
        ('Customer: ', 'Покупатель: '), ('Status: ', 'Статус: '),
        ('Category: ', 'Категория: '), ('Selected products: ', 'Выбрано товаров: '),
        ('Order dates: ', 'Даты заказов: '), ('Delivery lead: ', 'Срок поставки: '),
        ('Top 10 suppliers by purchase amount', 'Топ-10 поставщиков по сумме закупок'),
        ('Top 10 customers by sales amount', 'Топ-10 покупателей по сумме продаж'),
        ('Purchase amounts for listed top products', 'Суммы закупок по популярным товарам'),
        ('Sales amounts for listed top products', 'Суммы продаж по популярным товарам'),
    ):
        if value.startswith(source):
            value = target + value[len(source):]
            break
    for source, target in (
        (' orders; ', ' заказов; '), (' positions; all matching pages', ' позиций; все найденные страницы'),
        (' counterparties', ' контрагентов'), ('cancelled orders excluded', 'отменённые заказы не учитываются'),
        ('list search and status ignored', 'поиск и статус на странице не влияют'),
        ('unspecified unit', 'единица не указана'), ('All time', 'За всё время'), ('Today', 'Сегодня'),
        (' days; time zone: ', ' дней; часовой пояс: '),
        (' require attention; ', ' требуют внимания; '), (' out of stock; ', ' закончились; '),
        (' below minimum; ', ' ниже минимума; '), (' require order; ', ' требуют заказа; '),
        (' covered by incoming supply; ', ' покрываются ожидаемой поставкой; '), (' without forecast data', ' без данных для прогноза'),
    ):
        value = value.replace(source, target)
    if value.startswith('Top ') and value.endswith(' counterparties'):
        value = value.replace('Top ', 'Топ-', 1).replace(' counterparties', ' контрагентов')
    return value


def localize_workbook(workbook, company):
    """Translate report-owned labels while preserving user-entered text."""
    if getattr(company, 'language_code', 'ru') != 'ru':
        return workbook
    for sheet in workbook.worksheets:
        sheet.title = EXCEL_RU.get(sheet.title, sheet.title)
        for row in sheet.iter_rows():
            for cell in row:
                value = cell.value
                if not isinstance(value, str) or value.startswith('='):
                    continue
                cell.value = translate_report_text(value)
    return workbook


def money(value):
    return value.quantize(Decimal('0.01'))


def append_values(sheet, values):
    """Keep user-supplied text literal, including text starting with '='."""
    if not values:
        # openpyxl does not advance max_row for append([]). Create the spacer
        # row explicitly so the previous data row is not processed again.
        sheet.cell(row=sheet.max_row + 1, column=1, value=None)
        return
    sheet.append(values)
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = 's'
        elif isinstance(cell.value, datetime):
            if timezone.is_aware(cell.value):
                cell.value = timezone.localtime(cell.value).replace(tzinfo=None)
            cell.number_format = 'yyyy-mm-dd hh:mm'
        elif isinstance(cell.value, date):
            cell.number_format = 'yyyy-mm-dd'
        elif isinstance(cell.value, (Decimal, float)):
            cell.number_format = '#,##0.00'


def related_filter_name(orders, company, field_name, raw_value):
    """Resolve filter IDs to the same names users see in the application."""
    try:
        related_model = orders.model._meta.get_field(field_name).remote_field.model
        queryset = related_model.objects.filter(pk=raw_value)
        if any(field.name == 'company' for field in related_model._meta.fields):
            queryset = queryset.filter(company=company)
        related = queryset.first()
        if related and hasattr(related, 'display_name'):
            return related.display_name(company.language_code)
        return related.name if related else str(raw_value)
    except (LookupError, TypeError, ValueError):
        return str(raw_value)


def active_filters_text(orders, filters, company):
    values = []
    search = filters.get('search')
    if search:
        values.append(f'Search: {search}')
    for field_name, query_key, id_key, label in (
        ('supplier', 'supplier_query', 'supplier', 'Supplier'),
        ('customer', 'customer_query', 'customer', 'Customer'),
    ):
        if filters.get(query_key):
            values.append(f'{label}: {filters[query_key]}')
        elif filters.get(id_key):
            values.append(
                f'{label}: {related_filter_name(orders, company, field_name, filters[id_key])}'
            )
    if filters.get('status'):
        values.append(
            f'Status: {related_filter_name(orders, company, "status", filters["status"])}'
        )
    return '; '.join(values) if values else 'None'


def prepare_sheet(sheet, title, orders, filters, company, headers):
    append_values(sheet, [title])
    append_values(sheet, ['Generated at', timezone.now()])
    append_values(sheet, ['Active filters', active_filters_text(orders, filters, company)])
    append_values(sheet, ['Exported', ''])
    counts_row = sheet.max_row
    append_values(sheet, [])
    append_values(sheet, headers)
    return sheet.max_row, counts_row


def finish_sheet(sheet, header, last_data_row, order_keys=None):
    # Reports are read-only summaries. Filter arrows and frozen panes add visual
    # noise and previously obscured rows in the detailed product sections.
    sheet.freeze_panes = None
    sheet.auto_filter.ref = None
    sheet.sheet_view.showGridLines = False
    if order_keys is None:
        sheet.cell(1, 1).font = Font(size=15, bold=True, color='2E465D')
        for cell in sheet[header]:
            cell.fill = PatternFill('solid', fgColor='2E465D')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(wrap_text=True, vertical='center')
        sheet.row_dimensions[header].height = 32
        for column_index, column in enumerate(sheet.columns, start=1):
            width = max(len(str(cell.value or '')) for cell in column[header - 1:]) + 2
            sheet.column_dimensions[get_column_letter(column_index)].width = min(38, max(14, width))
        for row in sheet.iter_rows(min_row=header + 1):
            for cell in row:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
                if cell.row <= last_data_row and (cell.row - header) % 2 == 0:
                    cell.fill = PatternFill('solid', fgColor='F1F5F9')
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = 'landscape'
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.print_title_rows = f'{header}:{header}'
        return

    dark_fill = PatternFill('solid', fgColor='2E465D')
    light_fill = PatternFill('solid', fgColor='F8FAFC')
    group_fill = PatternFill('solid', fgColor='EEF3F7')
    border_side = Side(style='thin', color='B8C4CE')
    border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
    group_start_border = Border(top=Side(style='medium', color='91A4B5'))
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=sheet.max_column)
    for cell in sheet[1]:
        cell.fill = dark_fill
        cell.border = border
    sheet.cell(1, 1).font = Font(size=15, bold=True, color='FFFFFF')
    sheet.cell(1, 1).alignment = Alignment(horizontal='left', vertical='center')
    sheet.row_dimensions[1].height = 28
    for row_number in range(2, 5):
        sheet.merge_cells(
            start_row=row_number, start_column=2,
            end_row=row_number, end_column=sheet.max_column,
        )
        sheet.row_dimensions[row_number].height = 26
        for cell in sheet[row_number]:
            cell.fill = light_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        sheet.cell(row_number, 1).font = Font(bold=True, color='2E465D')
    for cell in sheet[header]:
        cell.fill = dark_fill
        cell.font = Font(color='FFFFFF', bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical='center')
        cell.border = border
    sheet.row_dimensions[header].height = 32
    for column_index, column in enumerate(sheet.columns, start=1):
        width = max(len(str(cell.value or '')) for cell in column[header - 1:]) + 2
        sheet.column_dimensions[get_column_letter(column_index)].width = min(38, max(14, width))
    group_index = -1
    previous_key = object()
    for row_number, order_key in zip(range(header + 1, last_data_row + 1), order_keys):
        is_group_start = order_key != previous_key
        if is_group_start:
            group_index += 1
            previous_key = order_key
        for cell in sheet[row_number]:
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            if group_index % 2 == 1:
                cell.fill = group_fill
            if is_group_start:
                cell.border = group_start_border
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = 'landscape'
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.print_title_rows = f'{header}:{header}'


def style_totals(sheet, title_row, last_row):
    dark_fill = PatternFill('solid', fgColor='2E465D')
    light_fill = PatternFill('solid', fgColor='F8FAFC')
    border_side = Side(style='thin', color='B8C4CE')
    border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
    sheet.merge_cells(start_row=title_row, start_column=1, end_row=title_row, end_column=4)
    for cell in sheet[title_row][:4]:
        cell.fill = dark_fill
        cell.border = border
    sheet.cell(title_row, 1).font = Font(bold=True, color='FFFFFF')
    sheet.row_dimensions[title_row].height = 24
    for row_number in range(title_row + 1, last_row + 1):
        sheet.row_dimensions[row_number].height = 22
        for cell in sheet[row_number][:4]:
            cell.fill = light_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        sheet.cell(row_number, 1).font = Font(bold=True, color='2E465D')


def build_order_report(orders, filters, company, kind, *, include_financial=True):
    supplier = kind == 'supplier'
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Orders'
    headers = ['Order #', 'Year', 'Created at', 'Supplier', 'Customer', 'Status']
    if supplier:
        headers.append('Track number')
    else:
        headers[3] = 'Product supplier'
    headers += ['SKU', 'Product', 'Quantity', 'Unit']
    if supplier:
        headers += ['Defective quantity', 'Defect rate, %']
        if include_financial:
            headers += ['Unit price, CNY', 'Total, CNY', 'CNY rate', 'Total, local', 'Currency']
    elif include_financial:
        headers += ['Unit price, local', 'Line discount, %', 'Order discount, %', 'Total, local', 'Currency']
    header, counts_row = prepare_sheet(
        sheet, f'{kind.title()} orders export', orders, filters, company, headers,
    )
    search = filters.get('search', '').strip()
    # When the search identifies SKUs, export only those positions, not unrelated
    # products that happen to share an order with them.
    sku_search = bool(search and orders.filter(items__product__sku__icontains=search).exists())
    quantities = defaultdict(lambda: ZERO)
    defective_quantities = defaultdict(lambda: ZERO)
    local_totals = defaultdict(lambda: ZERO)
    cny_total = ZERO
    order_ids = set()
    exported_positions = 0
    order_keys = []
    for order in orders.select_related('company').prefetch_related(
        'items__product__unit', 'items__product__supplier'
    ):
        items = list(order.items.all())
        if sku_search:
            items = [item for item in items if search.casefold() in item.product.sku.casefold()]
        if not items and sku_search:
            continue
        order_ids.add(order.pk)
        customer = order.customer.name if order.customer else ''
        status = order.status.display_name(company.language_code) if order.status else ''
        currency = (order.company_currency_code or company.base_currency_code) if supplier else company.base_currency_code
        prefix = [order.order_number, order.order_year, order.created_at, order.supplier.name if supplier else '', customer, status]
        if supplier:
            prefix.append(order.track_number or '')
        if not items:
            append_values(sheet, prefix + [''] * (len(headers) - len(prefix)))
            order_keys.append(order.pk)
        for item in items:
            product = item.product
            quantity = item.quantity or ZERO
            unit = item.unit or (product.unit.name if product.unit else '')
            row = list(prefix)
            if not supplier:
                row[3] = product.supplier.name if product.supplier else ''
            row += [product.sku, product.name, quantity, unit]
            if supplier:
                defective = item.defective_quantity or ZERO
                defect_rate = defective / quantity * 100 if quantity else ZERO
                row += [defective, money(defect_rate)]
                defective_quantities[unit] += defective
                if include_financial:
                    price = item.unit_price_cny if item.unit_price_cny is not None else product.purchase_price
                    price = price or ZERO
                    cny = money(quantity * price)
                    local = money(quantity * price * order.cny_to_local_rate)
                    row += [price, cny, order.cny_to_local_rate, local, currency]
                    cny_total += cny
            elif include_financial:
                price = item.unit_sale_price if item.unit_sale_price is not None else product.sale_price
                price = price or ZERO
                line_discount = item.discount_pct or ZERO
                order_discount = order.discount_pct or ZERO
                local = money(quantity * price * (Decimal('1') - line_discount) * (Decimal('1') - order_discount))
                row += [price, line_discount * 100, order_discount * 100, local, currency]
            append_values(sheet, row)
            order_keys.append(order.pk)
            exported_positions += 1
            if supplier and include_financial:
                sheet.cell(sheet.max_row, headers.index('CNY rate') + 1).number_format = '0.000000'
            quantities[unit] += quantity
            if include_financial:
                local_totals[currency] += local
    last_data_row = sheet.max_row
    append_values(sheet, [])
    append_values(sheet, ['Totals'])
    totals_title_row = sheet.max_row
    append_values(sheet, ['Orders count', len(order_ids)])
    append_values(sheet, ['Positions count', exported_positions])
    for unit, quantity in sorted(quantities.items()):
        append_values(sheet, [f'Total quantity, {unit or "unspecified unit"}', quantity])
    if supplier:
        for unit, defective in sorted(defective_quantities.items()):
            quantity = quantities[unit]
            rate = defective / quantity * 100 if quantity else ZERO
            append_values(sheet, [f'Defective quantity, {unit or "unspecified unit"}', defective, 'Defect rate, %', money(rate)])
        if include_financial:
            append_values(sheet, ['Total, CNY', cny_total])
    if include_financial:
        for currency, amount in sorted(local_totals.items()):
            append_values(sheet, [f'Total, {currency}', amount])
    sheet.cell(
        counts_row, 2,
        f'{len(order_ids)} orders; {exported_positions} positions; all matching pages',
    )
    finish_sheet(sheet, header, last_data_row, order_keys)
    style_totals(sheet, totals_title_row, sheet.max_row)
    localize_workbook(workbook, company)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer
