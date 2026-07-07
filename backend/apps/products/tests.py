from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from products.models import CompanySettings
from users.models import Company


class CompanySettingsCompanyScopeTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company_a = Company.objects.create(name='Company A')
        self.company_b = Company.objects.create(name='Company B')
        self.user_a = User.objects.create_user(
            username='user_a',
            email='a@example.com',
            password='password123',
            company=self.company_a,
            is_company_admin=True,
            is_email_verified=True,
        )
        self.user_b = User.objects.create_user(
            username='user_b',
            email='b@example.com',
            password='password123',
            company=self.company_b,
            is_email_verified=True,
        )
        self.user_a_member = User.objects.create_user(
            username='user_a_member',
            email='member-a@example.com',
            password='password123',
            company=self.company_a,
            is_email_verified=True,
        )

    def test_settings_are_created_per_company(self):
        self.client.force_authenticate(self.user_a)
        response_a = self.client.get('/api/settings/')

        self.client.force_authenticate(self.user_b)
        response_b = self.client.get('/api/settings/')

        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_a.data[0]['company'], self.company_a.id)
        self.assertEqual(response_b.data[0]['company'], self.company_b.id)
        self.assertNotEqual(response_a.data[0]['id'], response_b.data[0]['id'])

    def test_settings_update_does_not_affect_another_company(self):
        CompanySettings.objects.create(
            company=self.company_b,
            cny_to_local_rate=Decimal('10.000000'),
            usd_to_local_rate=Decimal('20.000000'),
            logistics_cost_per_kg_usd=Decimal('3.00'),
        )

        self.client.force_authenticate(self.user_a)
        response = self.client.post('/api/settings/', {
            'cny_to_local_rate': '77.000000',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            CompanySettings.objects.get(company=self.company_a).cny_to_local_rate,
            Decimal('77.000000'),
        )
        self.assertEqual(
            CompanySettings.objects.get(company=self.company_b).cny_to_local_rate,
            Decimal('10.000000'),
        )

    def test_non_admin_can_read_but_cannot_update_settings(self):
        self.client.force_authenticate(self.user_a_member)

        read_response = self.client.get('/api/settings/')
        write_response = self.client.post('/api/settings/', {
            'cny_to_local_rate': '88.000000',
        })

        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(write_response.status_code, 403)
