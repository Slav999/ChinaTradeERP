import json
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.request import urlopen

from django.utils import timezone


EXCHANGE_RATE_API_URL = 'https://open.er-api.com/v6/latest/{base}'


def decimal_rate(value):
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return None


def fetch_exchange_rate(base_currency, quote_currency, timeout=5):
    base_currency = (base_currency or '').upper()
    quote_currency = (quote_currency or '').upper()
    if not base_currency or not quote_currency:
        return None
    if base_currency == quote_currency:
        return Decimal('1.000000')

    url = EXCHANGE_RATE_API_URL.format(base=base_currency)
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    if payload.get('result') != 'success':
        return None
    return decimal_rate(payload.get('rates', {}).get(quote_currency))


def refresh_company_rates(company, settings, require_all=False):
    local_currency = (company.base_currency_code or '').upper()
    updated_fields = []

    cny_rate = fetch_exchange_rate('CNY', local_currency)
    usd_rate = fetch_exchange_rate('USD', local_currency)

    if require_all and (cny_rate is None or usd_rate is None):
        return False

    if cny_rate is not None:
        settings.cny_to_local_rate = cny_rate
        updated_fields.append('cny_to_local_rate')

    if usd_rate is not None:
        settings.usd_to_local_rate = usd_rate
        updated_fields.append('usd_to_local_rate')

    if updated_fields:
        settings.rates_updated_at = timezone.now()
        updated_fields.append('rates_updated_at')
        settings.save(update_fields=updated_fields)

    return bool(updated_fields)
