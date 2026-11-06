from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from supplier_orders.models import SupplierOrder, SupplierOrderStatus
from users.models import Company, CustomUser


class SampleOrderTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Samples company')
        self.user = CustomUser.objects.create_user(
            username='samples-owner', password='test', company=self.company,
            is_company_admin=True,
        )
        self.client.force_authenticate(self.user)
        self.supplier = Counterparty.objects.create(
            company=self.company, name='Sample factory', type='china', is_supplier=True,
        )
        self.status = SupplierOrderStatus.objects.filter(company=self.company).first()
        if self.status is None:
            self.status = SupplierOrderStatus.objects.create(company=self.company, name='New')

    def create_order(self, **kwargs):
        return SupplierOrder.objects.create(
            company=self.company, supplier=self.supplier, status=self.status, **kwargs,
        )

    def ids(self, **params):
        response = self.client.get('/api/supplier-order/', params)
        self.assertEqual(response.status_code, 200)
        return [row['id'] for row in response.data['results']]

    def test_minimal_sample_and_optional_trip(self):
        response = self.client.post('/api/supplier-order/', {
            'supplier_id': self.supplier.pk, 'is_sample': True,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        order = SupplierOrder.objects.get(pk=response.data['id'])
        self.assertTrue(order.is_sample)
        self.assertEqual(order.trip_name, '')
        self.assertEqual(order.items.count(), 0)
        self.assertIsNotNone(order.status_id)
        response = self.client.patch(f'/api/supplier-order/{order.pk}/', {
            'trip_name': 'Guangzhou exhibition',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.ids(is_sample='true', trip_name='guangzhou'), [order.pk])
        response = self.client.patch(f'/api/supplier-order/{order.pk}/', {
            'trip_name': '',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.trip_name, '')

    def test_separate_lists_search_and_company_isolation(self):
        regular = self.create_order()
        sample = self.create_order(is_sample=True, trip_name='Shenzhen exhibition')
        self.create_order(is_sample=True, trip_name='Guangzhou exhibition')
        other_company = Company.objects.create(name='Other company')
        other_supplier = Counterparty.objects.create(
            company=other_company, name='Other factory', type='china', is_supplier=True,
        )
        other_status = SupplierOrderStatus.objects.create(company=other_company, name='New')
        other = SupplierOrder.objects.create(
            company=other_company, supplier=other_supplier, status=other_status,
            is_sample=True, trip_name='Shenzhen exhibition',
        )
        self.assertEqual(self.ids(), [regular.pk])
        self.assertEqual(self.ids(is_sample='true', trip_name='shenzhen'), [sample.pk])
        self.assertEqual(self.ids(is_sample='true', search='shenzhen'), [sample.pk])
        self.assertEqual(self.client.get(f'/api/supplier-order/{other.pk}/').status_code, 404)
        detail = self.client.get(f'/api/supplier-order/{sample.pk}/')
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.data['is_sample'])
        self.assertEqual(detail.data['trip_name'], 'Shenzhen exhibition')

    def test_other_company_supplier_rejected(self):
        other_company = Company.objects.create(name='Foreign company')
        supplier = Counterparty.objects.create(
            company=other_company, name='Foreign factory', type='china', is_supplier=True,
        )
        response = self.client.post('/api/supplier-order/', {
            'supplier_id': supplier.pk, 'is_sample': True,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_independent_sample_numbering_and_no_reuse(self):
        regular = self.create_order(order_number='28')
        first = self.create_order(is_sample=True)
        second = self.create_order(is_sample=True)
        self.assertEqual((regular.order_number, first.order_number, second.order_number), ('28', '1', '2'))
        second.delete()
        self.assertEqual(self.create_order(is_sample=True).order_number, '3')
        self.assertEqual(self.create_order().order_number, '29')

    def test_existing_samples_are_renumbered_without_changing_regular_orders(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        regular = self.create_order(order_number='27')
        first = self.create_order(is_sample=True, order_number='28')
        second = self.create_order(is_sample=True, order_number='29')
        migration = import_module('supplier_orders.migrations.0017_separate_sample_numbering')
        with connection.schema_editor() as editor:
            migration.renumber_samples(apps, editor)
        regular.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((regular.order_number, first.order_number, second.order_number), ('27', '1', '2'))
        self.assertEqual(self.create_order(is_sample=True).order_number, '3')

    def test_order_type_cannot_change_after_creation(self):
        order = self.create_order()
        response = self.client.patch(f'/api/supplier-order/{order.pk}/', {'is_sample': True}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_empty_orders_cannot_send_or_generate_documents(self):
        from unittest.mock import patch
        from customer_orders.models import CustomerOrder, CustomerOrderStatus
        self.supplier.is_customer = True
        self.supplier.save()
        customer_status = CustomerOrderStatus.objects.create(company=self.company, name='Test new')
        customer = CustomerOrder.objects.create(
            company=self.company, customer=self.supplier, status=customer_status,
        )
        for order, kind in [(self.create_order(), 'supplier'), (self.create_order(is_sample=True), 'supplier'), (customer, 'customer')]:
            with self.subTest(kind=kind, order=order.pk):
                with patch(f'{kind}_orders.views.build_{kind}_order_pdf') as document, patch(f'{kind}_orders.views.EmailMessage') as email:
                    response = self.client.post(f'/api/{kind}-order/{order.pk}/send/')
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(response.data['detail'], 'Add at least one position before sending the order.')
                document.assert_not_called()
                email.assert_not_called()
                order.refresh_from_db()
                self.assertIsNone(order.sent_at)
