from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch
from rest_framework.test import APIClient, APITestCase

from products.models import CompanySettings
from users.models import Company, CompanyMembership


class RegistrationCompanyDefaultsTests(APITestCase):
    @patch('products.currency.refresh_company_rates')
    def test_register_sets_business_country_currency_and_example_tax(self, refresh_rates):
        response = self.client.post('/api/auth/register/', {
            'company_name': 'Kazakhstan Trade',
            'business_country': 'KZ',
            'username': 'owner',
            'email': 'owner@example.com',
            'password': 'StrongPass123',
            'password2': 'StrongPass123',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        company = Company.objects.get(name='Kazakhstan Trade')
        settings_obj = CompanySettings.objects.get(company=company)
        self.assertEqual(str(company.business_country), 'KZ')
        self.assertEqual(company.base_currency_code, 'KZT')
        self.assertEqual(company.base_currency_symbol, '₸')
        self.assertEqual(settings_obj.retail_tax_pct, Decimal('0.20'))
        refresh_rates.assert_called_once()


class CookieAuthenticationTests(APITestCase):
    def setUp(self):
        self.email = 'cookie-user@example.com'
        self.password = 'StrongPass123'
        self.user = get_user_model().objects.create_user(
            username='cookie_user',
            email=self.email,
            password=self.password,
            is_email_verified=True,
        )

    def login(self):
        return self.client.post('/api/auth/login/', {
            'email': self.email,
            'password': self.password,
        }, format='json')

    def test_login_sets_http_only_cookies_without_token_body(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertIn('HttpOnly', response.cookies[settings.JWT_ACCESS_COOKIE_NAME].OutputString())
        self.assertIn('HttpOnly', response.cookies[settings.JWT_REFRESH_COOKIE_NAME].OutputString())

    def test_cookie_access_token_authenticates_me_endpoint(self):
        self.login()

        response = self.client.get('/api/auth/me/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], self.email)

    def test_refresh_uses_cookie_and_sets_new_access_cookie(self):
        self.login()

        response = self.client.post('/api/auth/refresh/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('access', response.data)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)

    def test_cookie_authenticated_write_requires_csrf_header(self):
        client = APIClient(enforce_csrf_checks=True)
        login_response = client.post('/api/auth/login/', {
            'email': self.email,
            'password': self.password,
        }, format='json')
        csrf_token = login_response.cookies[settings.CSRF_COOKIE_NAME].value

        response_without_csrf = client.patch('/api/auth/me/', {
            'first_name': 'No csrf',
        }, format='json')
        response_with_csrf = client.patch('/api/auth/me/', {
            'first_name': 'With csrf',
        }, format='json', HTTP_X_CSRFTOKEN=csrf_token)

        self.assertEqual(response_without_csrf.status_code, 403)
        self.assertEqual(response_with_csrf.status_code, 200)
        self.assertEqual(response_with_csrf.data['first_name'], 'With csrf')

    def test_logout_clears_auth_cookies(self):
        self.login()

        response = self.client.post('/api/auth/logout/', {}, format='json')

        self.assertEqual(response.status_code, 205)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)
        self.assertEqual(response.cookies[settings.JWT_ACCESS_COOKIE_NAME]['max-age'], 0)
        self.assertEqual(response.cookies[settings.JWT_REFRESH_COOKIE_NAME]['max-age'], 0)


class EmployeeMembershipAdminTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Employees Ltd')
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='StrongPass123',
            company=self.company,
            is_company_admin=True,
            is_email_verified=True,
        )
        self.company.created_by = self.admin
        self.company.save(update_fields=['created_by'])
        self.employee = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='StrongPass123',
            company=self.company,
            is_email_verified=True,
        )
        self.admin_membership = CompanyMembership.objects.create(
            user=self.admin,
            company=self.company,
            role='admin',
            is_company_admin=True,
        )
        self.employee_membership = CompanyMembership.objects.create(
            user=self.employee,
            company=self.company,
            role='manager',
            position='Manager',
        )
        self.other_admin = User.objects.create_user(
            username='other_admin',
            email='other-admin@example.com',
            password='StrongPass123',
            company=self.company,
            is_company_admin=True,
            is_email_verified=True,
        )
        self.other_admin_membership = CompanyMembership.objects.create(
            user=self.other_admin,
            company=self.company,
            role='admin',
            is_company_admin=True,
        )

    def test_company_admin_can_list_employees(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get('/api/auth/employees/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual({item['email'] for item in response.data}, {
            self.admin.email,
            self.employee.email,
            self.other_admin.email,
        })

    def test_company_admin_can_dismiss_employee_without_deleting_account(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f'/api/auth/employees/{self.employee_membership.id}/dismiss/',
            {'reason': 'Left company'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.employee_membership.refresh_from_db()
        self.employee.refresh_from_db()
        self.assertEqual(self.employee_membership.status, CompanyMembership.STATUS_DISABLED)
        self.assertEqual(self.employee_membership.disable_reason, 'Left company')
        self.assertIsNotNone(self.employee_membership.disabled_at)
        self.assertEqual(self.employee.company, None)
        self.assertTrue(get_user_model().objects.filter(email=self.employee.email).exists())

    def test_disabled_active_company_blocks_authenticated_access(self):
        self.employee_membership.status = CompanyMembership.STATUS_DISABLED
        self.employee_membership.save(update_fields=['status'])
        self.client.post('/api/auth/login/', {
            'email': self.employee.email,
            'password': 'StrongPass123',
        }, format='json')

        response = self.client.get('/api/auth/me/')

        self.assertEqual(response.status_code, 401)

    def test_company_creator_can_dismiss_another_admin(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f'/api/auth/employees/{self.other_admin_membership.id}/dismiss/',
            {'reason': 'Admin left'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.other_admin_membership.refresh_from_db()
        self.assertEqual(self.other_admin_membership.status, CompanyMembership.STATUS_DISABLED)

    def test_non_creator_admin_cannot_dismiss_another_admin(self):
        self.client.force_authenticate(self.other_admin)

        response = self.client.post(
            f'/api/auth/employees/{self.admin_membership.id}/dismiss/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_company_admin_cannot_dismiss_self(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f'/api/auth/employees/{self.admin_membership.id}/dismiss/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
