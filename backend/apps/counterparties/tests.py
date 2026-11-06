from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from counterparties.models import Counterparty, CounterpartyStatus
from customer_orders.models import CustomerOrder, CustomerOrderStatus
from products.models import Product
from users.models import Company


class CounterpartyOrderingTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Counterparty Co')
        self.user = User.objects.create_user(
            username='counterparty-user',
            email='counterparty@example.com',
            password='password123',
            company=self.company,
            is_email_verified=True,
        )
        self.client.force_authenticate(self.user)

    def test_newest_counterparties_are_listed_first(self):
        first = Counterparty.objects.create(
            company=self.company,
            name='Alpha',
            type='local',
            is_customer=True,
        )
        second = Counterparty.objects.create(
            company=self.company,
            name='Beta',
            type='local',
            is_customer=True,
        )

        response = self.client.get('/api/counterparties/')

        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.data['results']]
        self.assertEqual(ids[:2], [second.id, first.id])


class CounterpartyStatusLanguageTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Status Language Co', language_code='en')
        self.user = User.objects.create_user(
            username='status-language-user',
            email='status-language@example.com',
            password='password123',
            company=self.company,
            notification_language='ru',
            is_email_verified=True,
        )
        self.status = CounterpartyStatus.objects.create(
            company=self.company,
            name='On hold',
            translations={'en': 'On hold', 'ru': 'Приостановлен'},
        )
        self.client.force_authenticate(self.user)

    def test_status_display_name_uses_employee_language(self):
        response = self.client.get('/api/counterparty-statuses/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['display_name'], 'Приостановлен')

        self.user.notification_language = 'en'
        self.user.save(update_fields=['notification_language'])
        response = self.client.get('/api/counterparty-statuses/')
        self.assertEqual(response.data[0]['display_name'], 'On hold')


class CounterpartyDeleteTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Delete Co')
        self.user = User.objects.create_user(
            username='delete-user',
            role='manager',
            email='delete@example.com',
            password='password123',
            company=self.company,
            is_email_verified=True,
        )
        self.client.force_authenticate(self.user)

    def create_supplier(self, name='Supplier'):
        return Counterparty.objects.create(
            company=self.company,
            name=name,
            type='china',
            is_supplier=True,
        )

    def test_can_delete_counterparty_used_only_by_archived_products(self):
        supplier = self.create_supplier()
        product = Product.objects.create(
            company=self.company,
            name='Archived product',
            sku='ARCH-1',
            supplier=supplier,
            is_archived=True,
        )

        response = self.client.delete(f'/api/counterparties/{supplier.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Counterparty.objects.filter(id=supplier.id).exists())
        self.assertFalse(Product.objects.filter(id=product.id).exists())

    def test_cannot_delete_counterparty_used_by_active_products(self):
        supplier = self.create_supplier()
        Product.objects.create(
            company=self.company,
            name='Active product',
            sku='ACTIVE-1',
            supplier=supplier,
        )

        response = self.client.delete(f'/api/counterparties/{supplier.id}/')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'],
            'Counterparty is used by active products and cannot be deleted.',
        )
        self.assertTrue(Counterparty.objects.filter(id=supplier.id).exists())

    def test_cannot_delete_counterparty_used_by_customer_orders(self):
        customer = Counterparty.objects.create(
            company=self.company,
            name='Customer',
            type='local',
            is_customer=True,
        )
        status = CustomerOrderStatus.objects.create(
            company=self.company,
            name='New',
        )
        CustomerOrder.objects.create(
            company=self.company,
            order_number='1',
            status=status,
            customer=customer,
        )

        response = self.client.delete(f'/api/counterparties/{customer.id}/')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'],
            'Counterparty is used by customer orders and cannot be deleted.',
        )
        self.assertTrue(Counterparty.objects.filter(id=customer.id).exists())


class CounterpartyCreateTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Create Co')
        self.user = User.objects.create_user(
            username='create-user',
            role='manager',
            email='create@example.com',
            password='password123',
            company=self.company,
            is_email_verified=True,
        )
        self.client.force_authenticate(self.user)

    def test_unique_code_is_generated_when_omitted(self):
        response = self.client.post('/api/counterparties/', {
            'name': 'Quick Supplier',
            'type': 'china',
            'is_supplier': True,
            'is_customer': False,
        })

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['unique_code'].startswith('CN-'))
