from decimal import Decimal

from babel import Locale
from babel.numbers import get_currency_symbol, get_territory_currencies


DEFAULT_COUNTRY = 'KZ'
DEFAULT_CURRENCY = 'KZT'
DEFAULT_LOCALE = 'ru_KZ'
DEFAULT_TAX_RATE = Decimal('0.20')

LOCALE_BY_COUNTRY = {
    'AM': 'hy_AM',
    'AZ': 'az_AZ',
    'BY': 'ru_BY',
    'GE': 'ka_GE',
    'KG': 'ru_KG',
    'KZ': 'ru_KZ',
    'MD': 'ro_MD',
    'RU': 'ru_RU',
    'TJ': 'ru_TJ',
    'TM': 'ru_TM',
    'UA': 'uk_UA',
    'UZ': 'uz_UZ',
}

def normalize_country_code(country_code):
    if hasattr(country_code, 'code'):
        country_code = country_code.code
    return str(country_code or DEFAULT_COUNTRY).strip().upper()[:2]


def locale_for_country(country_code):
    country_code = normalize_country_code(country_code)
    if country_code in LOCALE_BY_COUNTRY:
        return LOCALE_BY_COUNTRY[country_code]
    return f'en_{country_code}'


def currency_for_country(country_code):
    country_code = normalize_country_code(country_code)
    try:
        currencies = get_territory_currencies(country_code)
    except Exception:
        currencies = []
    return currencies[0] if currencies else DEFAULT_CURRENCY


def currency_symbol(currency_code, locale_code=None):
    locale_code = locale_code or DEFAULT_LOCALE
    try:
        return get_currency_symbol(currency_code, locale=locale_code)
    except Exception:
        return currency_code


def country_display_name(country_code):
    country_code = normalize_country_code(country_code)
    locale_code = locale_for_country(country_code)
    try:
        locale = Locale.parse(locale_code)
        return locale.territories.get(country_code, country_code)
    except Exception:
        return country_code


def company_defaults_for_country(country_code):
    country_code = normalize_country_code(country_code)
    locale_code = locale_for_country(country_code)
    currency_code = currency_for_country(country_code)
    return {
        'business_country': country_code,
        'base_currency_code': currency_code,
        'base_currency_symbol': currency_symbol(currency_code, locale_code),
        'locale_code': locale_code,
        'retail_tax_pct': DEFAULT_TAX_RATE,
    }
