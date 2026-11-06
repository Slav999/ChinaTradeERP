import glob
import io
import os
from decimal import Decimal
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageOps, UnidentifiedImageError

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _register_font():
    candidates = [
        r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\segoeui.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/local/share/fonts/dejavu/DejaVuSans.ttf',
    ]
    candidates.extend(glob.glob('/usr/share/fonts/**/DejaVuSans.ttf', recursive=True))
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('ERPFont', path))
                return 'ERPFont'
            except Exception:
                continue
    return 'Helvetica'


FONT_NAME = _register_font()


def _styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        'ERPBody',
        parent=base['BodyText'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=13,
    )
    return {
        'title': ParagraphStyle(
            'ERPTitle',
            parent=body,
            fontSize=18,
            leading=22,
            spaceAfter=4,
        ),
        'subtitle': ParagraphStyle(
            'ERPSubtitle',
            parent=body,
            textColor=colors.HexColor('#6c757d'),
        ),
        'body': body,
        'small': ParagraphStyle(
            'ERPSmall',
            parent=body,
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#6c757d'),
        ),
        'company_title': ParagraphStyle(
            'ERPCompanyTitle',
            parent=body,
            fontSize=15,
            leading=18,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#2f455c'),
        ),
        'company_contacts': ParagraphStyle(
            'ERPCompanyContacts',
            parent=body,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#6c757d'),
        ),
        'right': ParagraphStyle(
            'ERPRight',
            parent=body,
            alignment=TA_RIGHT,
        ),
    }


def _p(value, style):
    value = '' if value is None else str(value)
    return Paragraph(value.replace('\n', '<br/>'), style)


def _money(value, currency_code=''):
    amount = Decimal(value or '0').quantize(Decimal('0.01'))
    return f'{amount} {currency_code}'.strip()


def _qty(value):
    value = Decimal(value or '0')
    normalized = value.normalize()
    return format(normalized, 'f')


def _pct(value):
    value = (Decimal(value or '0') * Decimal('100')).quantize(Decimal('0.01'))
    return f'{value}%'


def _document_date():
    return timezone.localtime(timezone.now()).strftime('%d.%m.%Y')


def _company_header(company, styles):
    left = []
    if company.logo:
        try:
            left.append(Image(company.logo.path, width=48 * mm, height=30 * mm, kind='proportional'))
        except Exception:
            left.append(_p(company.name, styles['title']))
    else:
        left.append(_p(company.name, styles['title']))

    contacts = []
    if company.work_email:
        contacts.append(company.work_email)
    if company.phone:
        contacts.append(company.phone)
    if company.address:
        contacts.append(company.address)

    right = [_p(company.name, styles['company_title'])]
    if contacts:
        right.append(_p('<br/>'.join(contacts), styles['company_contacts']))

    table = Table([[left, right]], colWidths=[62 * mm, 108 * mm])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    return table


def _details_table(rows, styles):
    data = [[_p(label, styles['small']), _p(value, styles['body'])] for label, value in rows if value]
    if not data:
        return Spacer(1, 1)
    table = Table(data, colWidths=[38 * mm, 132 * mm], hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table


def _items_table(headers, rows, widths):
    table = Table([headers, *rows], colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2f455c')),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEADING', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table


def _product_thumbnail(product):
    """Embed a small, oriented image; unavailable product media must not block a PDF."""
    if not product.image:
        return ''
    try:
        with product.image.open('rb') as source:
            with PILImage.open(source) as original:
                picture = ImageOps.exif_transpose(original).convert('RGBA')
                picture.thumbnail((240, 240), PILImage.Resampling.LANCZOS)
                canvas = PILImage.new('RGB', (240, 240), 'white')
                canvas.paste(picture, ((240 - picture.width) // 2, (240 - picture.height) // 2), picture)
                buffer = io.BytesIO()
                canvas.save(buffer, format='PNG')
        buffer.seek(0)
        return Image(buffer, width=16 * mm, height=16 * mm)
    except (OSError, ValueError, UnidentifiedImageError, PILImage.DecompressionBombError):
        return ''


def build_supplier_order_pdf(order):
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    story = [
        _company_header(order.company, styles),
        Spacer(1, 8),
        _p(f'Supplier order #{order.order_number}', styles['title']),
        _details_table([
            ('Company', order.company.name),
            ('Supplier', order.supplier.name if order.supplier else ''),
            ('Date', _document_date()),
            ('Shipping address', order.shipping_address),
            ('Comment for supplier', order.supplier_comment),
        ], styles),
        Spacer(1, 8),
    ]

    rows = []
    for index, item in enumerate(order.items.select_related('product', 'product__unit').all(), start=1):
        rows.append([
            str(index),
            _product_thumbnail(item.product),
            _p(item.product.sku, styles['body']),
            _p(item.product.name, styles['body']),
            _qty(item.quantity),
            item.product.unit.name if item.product.unit else item.unit,
        ])
    if not rows:
        rows.append(['', '', _p('No items', styles['body']), '', '', ''])
    story.append(_items_table(
        ['#', 'Photo', 'SKU', 'Product', 'Qty', 'Unit'],
        rows,
        [8 * mm, 20 * mm, 30 * mm, 68 * mm, 22 * mm, 22 * mm],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def build_customer_order_pdf(order):
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    currency = order.company.base_currency_code or ''
    story = [
        _company_header(order.company, styles),
        Spacer(1, 8),
        _p(f'Commercial offer #{order.order_number}', styles['title']),
        _details_table([
            ('Company', order.company.name),
            ('Customer', order.customer.name if order.customer else ''),
            ('Date', _document_date()),
            ('Shipping address', order.shipping_address),
            ('Comment for customer', order.customer_comment),
            ('Bank details', order.company.bank_details),
        ], styles),
        Spacer(1, 8),
    ]

    items = list(order.items.select_related('product', 'product__unit').all())
    has_line_discounts = any((item.discount_pct or Decimal('0.0000')) > 0 for item in items)
    rows = []
    subtotal = Decimal('0.00')
    line_discount_total = Decimal('0.00')
    for index, item in enumerate(items, start=1):
        unit_price = getattr(item, 'unit_sale_price', None)
        if unit_price is None:
            unit_price = item.product.sale_price or Decimal('0.00')
        quantity = item.quantity or Decimal('0.00')
        line_discount = item.discount_pct or Decimal('0.0000')
        line_subtotal = (unit_price * quantity).quantize(Decimal('0.01'))
        line_discount_amount = (line_subtotal * line_discount).quantize(Decimal('0.01'))
        line_total = (unit_price * quantity * (Decimal('1.0000') - line_discount)).quantize(Decimal('0.01'))
        subtotal += line_subtotal
        line_discount_total += line_discount_amount
        row = [
            str(index),
            _product_thumbnail(item.product),
            _p(f'{escape(item.product.sku)}<br/>{escape(item.product.name)}', styles['body']),
            _qty(quantity),
            item.product.unit.name if item.product.unit else item.unit,
            _p(_money(unit_price, currency), styles['right']),
            _p(_money(line_total, currency), styles['right']),
        ]
        if has_line_discounts:
            row.insert(-1, _pct(line_discount) if line_discount else '')
        rows.append(row)
    if not rows:
        rows.append(['', '', _p('No items', styles['body']), '', '', '', ''])
        if has_line_discounts:
            rows[0].insert(-1, '')
    headers = ['#', 'Photo', 'SKU / Product', 'Qty', 'Unit', 'Price', 'Total']
    widths = [8 * mm, 20 * mm, 52 * mm, 16 * mm, 15 * mm, 29 * mm, 30 * mm]
    if has_line_discounts:
        headers.insert(-1, 'Discount')
        widths = [8 * mm, 20 * mm, 42 * mm, 15 * mm, 12 * mm, 27 * mm, 18 * mm, 28 * mm]
    story.append(_items_table(
        headers,
        rows,
        widths,
    ))

    subtotal_after_line_discounts = (subtotal - line_discount_total).quantize(Decimal('0.01'))
    order_discount = (subtotal_after_line_discounts * (order.discount_pct or Decimal('0.0000'))).quantize(Decimal('0.01'))
    total = (subtotal_after_line_discounts - order_discount).quantize(Decimal('0.01'))
    totals = []
    if line_discount_total or order_discount:
        totals.append([_p('Subtotal', styles['right']), _p(_money(subtotal, currency), styles['right'])])
    if line_discount_total:
        totals.append([_p('Line discounts', styles['right']), _p(_money(line_discount_total, currency), styles['right'])])
    if order_discount:
        totals.append([_p(f'Order discount ({_pct(order.discount_pct)})', styles['right']), _p(_money(order_discount, currency), styles['right'])])
    totals.append([_p('Total', styles['right']), _p(_money(total, currency), styles['right'])])
    totals_table = Table(totals, colWidths=[115 * mm, 55 * mm], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, -1), (-1, -1), 0.6, colors.HexColor('#dee2e6')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#2f455c')),
    ]))
    story.extend([Spacer(1, 8), KeepTogether([totals_table])])

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
