from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

import pytz
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from products.models import CompanySettings

from .models import StockControlSnapshot, StockMovement, WarehouseStock


ZERO = Decimal('0.00')
MONTH_DAYS = Decimal('30')
QUANTITY_STEP = Decimal('0.01')

STATUS_OUT_OF_STOCK = 'out_of_stock'
STATUS_BELOW_MINIMUM = 'below_minimum'
STATUS_REQUIRES_ORDER = 'requires_order'
STATUS_SUPPLY_EXPECTED = 'supply_expected'
# Kept for compatibility with previously saved snapshots. New calculations expose
# missing history through forecast_quality instead of using it as a stock status.
STATUS_NO_FORECAST = 'no_forecast'
STATUS_NORMAL = 'normal'

STATUS_LABELS = {
    STATUS_OUT_OF_STOCK: 'Out of stock',
    STATUS_BELOW_MINIMUM: 'Below minimum',
    STATUS_REQUIRES_ORDER: 'Order required',
    STATUS_SUPPLY_EXPECTED: 'Incoming supply covers demand',
    STATUS_NO_FORECAST: 'No forecast data',
    STATUS_NORMAL: 'Normal',
}
STATUS_PRIORITY = {
    STATUS_OUT_OF_STOCK: 0,
    STATUS_BELOW_MINIMUM: 1,
    STATUS_REQUIRES_ORDER: 2,
    STATUS_SUPPLY_EXPECTED: 3,
    STATUS_NO_FORECAST: 4,
    STATUS_NORMAL: 5,
}

FORECAST_QUALITY_LABELS = {
    'insufficient': 'No data',
    'preliminary': 'Preliminary',
    'sufficient': 'Reliable',
    'manual': 'Manual',
}


def quantity(value):
    return Decimal(value or ZERO).quantize(QUANTITY_STEP, rounding=ROUND_HALF_UP)


def company_stock_settings(company):
    settings, _ = CompanySettings.objects.get_or_create(
        company=company,
        defaults=CompanySettings.default_values(company.business_country),
    )
    return settings


def stock_control_rows(company, settings=None):
    settings = settings or company_stock_settings(company)
    stocks = list(WarehouseStock.objects.filter(
        company=company,
        product__is_stock_item=True,
        product__is_archived=False,
        product__minimum_stock_level__isnull=False,
    ).select_related('product', 'product__unit', 'product__supplier'))
    consumption_context = automatic_consumption_context(
        company,
        settings,
        [stock.product for stock in stocks],
    )

    rows = [
        stock_control_item(stock, settings, consumption_context)
        for stock in stocks
    ]

    rows.sort(key=lambda row: (
        STATUS_PRIORITY[row['status']],
        -Decimal(row['shortage_at_delivery'] or ZERO),
        row['product_name'].casefold(),
        row['sku'].casefold(),
    ))
    return rows


def _company_timezone(settings):
    try:
        return pytz.timezone(settings.stock_timezone)
    except pytz.UnknownTimeZoneError:
        return pytz.UTC


def automatic_consumption_context(company, settings, products=None):
    products = list(products or company.products.filter(
        is_stock_item=True,
        is_archived=False,
    ))
    automatic_products = [
        product for product in products
        if product.consumption_calculation_mode == product.CONSUMPTION_MODE_AUTOMATIC
    ]
    if not automatic_products:
        return {}

    history_days = int(settings.stock_consumption_history_days)
    today = company_local_date(settings)
    window_start = today - timedelta(days=history_days - 1)
    aggregates = {
        row['product_id']: row
        for row in StockMovement.objects.filter(
            company=company,
            product_id__in=[product.id for product in automatic_products],
            movement_type=StockMovement.TYPE_CUSTOMER_SHIPPED,
            created_at__date__gte=window_start,
            created_at__date__lte=today,
        ).values('product_id').annotate(
            total=Sum('quantity'),
            shipment_count=Count('id'),
        )
    }
    zone = _company_timezone(settings)
    result = {}
    for product in automatic_products:
        product_date = timezone.localtime(product.created_at, zone).date()
        observation_start = max(window_start, product_date)
        observed_days = max((today - observation_start).days + 1, 1)
        aggregate = aggregates.get(product.id, {})
        total = quantity(aggregate.get('total'))
        if observed_days < 30:
            monthly = None
            confidence = 'insufficient'
        else:
            monthly = quantity(total * MONTH_DAYS / Decimal(observed_days))
            confidence = 'sufficient' if observed_days >= 90 else 'preliminary'
        result[product.id] = {
            'monthly_consumption': monthly,
            'confidence': confidence,
            'observed_days': observed_days,
            'shipment_count': aggregate.get('shipment_count', 0),
            'history_window_days': history_days,
        }
    return result


def stock_control_item(stock, settings, consumption_context=None):
    product = stock.product
    minimum = quantity(product.minimum_stock_level)
    if product.consumption_calculation_mode == product.CONSUMPTION_MODE_AUTOMATIC:
        if consumption_context is None:
            consumption_context = automatic_consumption_context(
                product.company,
                settings,
                [product],
            )
        consumption = consumption_context.get(product.id, {})
        monthly_consumption = consumption.get('monthly_consumption')
        consumption_source = 'automatic'
        consumption_confidence = consumption.get('confidence', 'insufficient')
        consumption_observed_days = consumption.get('observed_days', 0)
        consumption_shipment_count = consumption.get('shipment_count', 0)
        consumption_history_window_days = consumption.get(
            'history_window_days',
            int(settings.stock_consumption_history_days),
        )
    else:
        monthly_consumption = (
            quantity(product.average_monthly_consumption)
            if product.average_monthly_consumption is not None else None
        )
        consumption_source = 'manual'
        consumption_confidence = 'manual' if monthly_consumption is not None else 'insufficient'
        consumption_observed_days = None
        consumption_shipment_count = None
        consumption_history_window_days = None
    has_consumption_data = monthly_consumption is not None
    purchase_batch_size = (
        quantity(product.purchase_batch_size)
        if product.purchase_batch_size is not None else None
    )
    on_hand = quantity(stock.quantity_on_hand)
    defective = quantity(stock.quantity_defective)
    physical = quantity(on_hand + defective)
    reserved = quantity(stock.quantity_reserved)
    available = quantity(max(on_hand - reserved, ZERO))
    expected = quantity(stock.quantity_expected)
    lead_days = Decimal(settings.stock_delivery_lead_days)

    if has_consumption_data:
        consumption_during_lead = quantity(monthly_consumption * lead_days / MONTH_DAYS)
        forecast_without_incoming = quantity(available - consumption_during_lead)
        projected = quantity(available + expected - consumption_during_lead)
        shortage = quantity(max(minimum - projected, ZERO))
        if shortage == ZERO:
            recommended = ZERO
        elif purchase_batch_size:
            batch_count = (shortage / purchase_batch_size).to_integral_value(rounding=ROUND_CEILING)
            recommended = quantity(batch_count * purchase_batch_size)
        else:
            recommended = None
    else:
        consumption_during_lead = None
        forecast_without_incoming = None
        projected = None
        shortage = None
        recommended = None

    if available <= ZERO:
        status = STATUS_OUT_OF_STOCK
    elif available <= minimum:
        status = STATUS_BELOW_MINIMUM
    elif not has_consumption_data:
        status = STATUS_NORMAL
    elif projected < minimum:
        status = STATUS_REQUIRES_ORDER
    elif expected > ZERO and forecast_without_incoming < minimum <= projected:
        status = STATUS_SUPPLY_EXPECTED
    else:
        status = STATUS_NORMAL

    return {
        'product_id': product.id,
        'sku': product.sku,
        'product_name': product.name,
        'supplier_name': product.supplier.name,
        'unit': product.unit.name if product.unit else '',
        'quantity_on_hand': str(on_hand),
        'quantity_defective': str(defective),
        'quantity_physical': str(physical),
        'quantity_reserved': str(reserved),
        'quantity_available': str(available),
        'minimum_stock_level': str(minimum),
        'quantity_expected': str(expected),
        'average_monthly_consumption': (
            str(monthly_consumption) if monthly_consumption is not None else None
        ),
        'purchase_batch_size': (
            str(purchase_batch_size) if purchase_batch_size is not None else None
        ),
        'has_consumption_data': has_consumption_data,
        'consumption_source': consumption_source,
        'consumption_confidence': consumption_confidence,
        'forecast_quality': consumption_confidence,
        'forecast_quality_label': FORECAST_QUALITY_LABELS.get(
            consumption_confidence,
            consumption_confidence.replace('_', ' ').title(),
        ),
        'consumption_observed_days': consumption_observed_days,
        'consumption_shipment_count': consumption_shipment_count,
        'consumption_history_window_days': consumption_history_window_days,
        'delivery_lead_days': int(settings.stock_delivery_lead_days),
        'consumption_during_lead': (
            str(consumption_during_lead) if consumption_during_lead is not None else None
        ),
        'projected_stock': str(projected) if projected is not None else None,
        'shortage_at_delivery': str(shortage) if shortage is not None else None,
        'recommended_order_quantity': (
            str(recommended) if recommended is not None else None
        ),
        'status': status,
        'status_label': STATUS_LABELS[status],
    }


def stock_control_summary(rows):
    counts = {status: 0 for status in STATUS_LABELS}
    for row in rows:
        counts[row['status']] += 1
    attention_count = (
        counts[STATUS_OUT_OF_STOCK]
        + counts[STATUS_BELOW_MINIMUM]
        + counts[STATUS_REQUIRES_ORDER]
        + counts[STATUS_SUPPLY_EXPECTED]
    )
    return {
        'total_count': len(rows),
        'attention_count': attention_count,
        'critical_count': counts[STATUS_OUT_OF_STOCK] + counts[STATUS_BELOW_MINIMUM],
        'out_of_stock_count': counts[STATUS_OUT_OF_STOCK],
        'below_minimum_count': counts[STATUS_BELOW_MINIMUM],
        'requires_order_count': counts[STATUS_REQUIRES_ORDER],
        'supply_expected_count': counts[STATUS_SUPPLY_EXPECTED],
        'no_forecast_count': sum(
            1 for row in rows if not row['has_consumption_data']
        ),
        'normal_count': counts[STATUS_NORMAL],
    }


def live_stock_control_data(company, settings=None):
    settings = settings or company_stock_settings(company)
    rows = stock_control_rows(company, settings)
    return {
        'id': None,
        'schedule_date': company_local_date(settings),
        'source': 'live',
        'source_display': 'Live',
        'generated_at': timezone.now(),
        'delivery_lead_days': settings.stock_delivery_lead_days,
        'timezone_name': settings.stock_timezone,
        'summary': stock_control_summary(rows),
        'items': rows,
        'is_dismissed': False,
    }


def generate_stock_control_snapshot(company, source, schedule_date, user=None):
    settings = company_stock_settings(company)
    rows = stock_control_rows(company, settings)
    defaults = {
        'generated_by': user,
        'generated_at': timezone.now(),
        'delivery_lead_days': settings.stock_delivery_lead_days,
        'timezone_name': settings.stock_timezone,
        'summary': stock_control_summary(rows),
        'items': rows,
    }
    with transaction.atomic():
        snapshot, _ = StockControlSnapshot.objects.update_or_create(
            company=company,
            schedule_date=schedule_date,
            source=source,
            defaults=defaults,
        )
        snapshot.dismissals.all().delete()
    return snapshot


def company_local_date(settings, instant=None):
    instant = instant or timezone.now()
    zone = _company_timezone(settings)
    return instant.astimezone(zone).date()


def latest_scheduled_date(settings, instant=None):
    instant = instant or timezone.now()
    zone = _company_timezone(settings)
    local_now = instant.astimezone(zone)
    days_since = (local_now.weekday() - settings.stock_notification_weekday) % 7
    scheduled_date = local_now.date() - timedelta(days=days_since)
    scheduled_local = zone.localize(datetime.combine(
        scheduled_date,
        settings.stock_notification_time,
    ))
    if local_now < scheduled_local:
        scheduled_date -= timedelta(days=7)
    return scheduled_date


def ensure_due_stock_control_snapshot(company, user=None, instant=None):
    settings = company_stock_settings(company)
    if not settings.stock_weekly_control_enabled:
        return None
    schedule_date = latest_scheduled_date(settings, instant)
    snapshot = StockControlSnapshot.objects.filter(
        company=company,
        schedule_date=schedule_date,
        source=StockControlSnapshot.SOURCE_SCHEDULED,
    ).first()
    if snapshot:
        return snapshot
    return generate_stock_control_snapshot(
        company,
        StockControlSnapshot.SOURCE_SCHEDULED,
        schedule_date,
        user,
    )
