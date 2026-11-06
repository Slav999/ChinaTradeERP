import pytz
from django.utils import timezone
from users.company_defaults import normalize_country_code


def company_year(company, instant=None):
    country = normalize_country_code(company.business_country)
    primary = {'KZ': 'Asia/Almaty', 'RU': 'Europe/Moscow', 'CN': 'Asia/Shanghai', 'US': 'America/New_York'}
    zone = primary.get(country) or next(iter(pytz.country_timezones.get(country, [])), 'UTC')
    return (instant or timezone.now()).astimezone(pytz.timezone(zone)).year
