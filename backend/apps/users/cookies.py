from django.conf import settings
from django.middleware.csrf import get_token


def cookie_max_age(jwt_setting_name):
    return int(settings.SIMPLE_JWT[jwt_setting_name].total_seconds())


def set_auth_cookies(response, access_token, refresh_token=None, request=None):
    cookie_options = {
        'path': settings.JWT_COOKIE_PATH,
        'secure': settings.JWT_COOKIE_SECURE,
        'httponly': True,
        'samesite': settings.JWT_COOKIE_SAMESITE,
    }
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        access_token,
        max_age=cookie_max_age('ACCESS_TOKEN_LIFETIME'),
        **cookie_options,
    )

    if refresh_token:
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            refresh_token,
            max_age=cookie_max_age('REFRESH_TOKEN_LIFETIME'),
            **cookie_options,
        )

    if request is not None:
        get_token(request)

    return response


def clear_auth_cookies(response):
    delete_options = {
        'path': settings.JWT_COOKIE_PATH,
        'samesite': settings.JWT_COOKIE_SAMESITE,
    }
    response.delete_cookie(settings.JWT_ACCESS_COOKIE_NAME, **delete_options)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE_NAME, **delete_options)
    return response
