from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import CompanyMembership


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            auth_result = super().authenticate(request)
            if auth_result is not None:
                self.validate_active_company(auth_result[0])
            return auth_result

        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE_NAME)
        if raw_token is None:
            return None

        self.enforce_csrf(request)
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        self.validate_active_company(user)
        return user, validated_token

    def validate_active_company(self, user):
        if not user.company_id:
            return
        has_active_membership = CompanyMembership.objects.filter(
            user=user,
            company_id=user.company_id,
            status=CompanyMembership.STATUS_ACTIVE,
        ).exists()
        if not has_active_membership:
            raise AuthenticationFailed('Your access to this company is disabled.')

    def enforce_csrf(self, request):
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return

        django_request = getattr(request, '_request', request)

        def dummy_get_response(_request):
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(django_request)
        reason = check.process_view(django_request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')
