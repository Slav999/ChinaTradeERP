from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase
from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderStatus
from supplier_orders.models import SupplierOrder, SupplierOrderStatus
from users.models import Company
from core.order_numbering import company_year


class AnnualOrderNumberTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Annual', business_country='KZ')
        self.party = Counterparty.objects.create(company=self.company, name='Factory', type='china', is_supplier=True, is_customer=True)
        self.ss = SupplierOrderStatus.objects.create(company=self.company, name='New')
        self.cs = CustomerOrderStatus.objects.create(company=self.company, name='New')

    def make(self, model):
        kwargs = {'company': self.company, 'status': self.ss if model is SupplierOrder else self.cs}
        kwargs['supplier' if model is SupplierOrder else 'customer'] = self.party
        return model.objects.create(**kwargs)

    def test_annual_reset_separate_types_and_no_reuse_after_delete(self):
        for model in (SupplierOrder, CustomerOrder):
            with self.subTest(model=model.__name__):
                with patch('core.order_numbering.timezone.now', return_value=datetime(2026, 12, 31, 18, 59, tzinfo=timezone.utc)):
                    old = self.make(model)
                    second = self.make(model)
                    self.assertEqual((old.order_number, second.order_number, old.order_year), ('1', '2', 2026))
                    second.delete()
                    self.assertEqual(self.make(model).order_number, '3')
                with patch('core.order_numbering.timezone.now', return_value=datetime(2026, 12, 31, 19, 0, tzinfo=timezone.utc)):
                    new = self.make(model)
                    self.assertEqual((new.order_number, new.order_year), ('1', 2027))
                    old.save()
                    old.refresh_from_db()
                    self.assertEqual((old.order_number, old.order_year), ('1', 2026))
                    self.assertTrue(old.is_previous_year)
                    self.assertFalse(new.is_previous_year)

    def test_country_boundary_and_independent_company(self):
        instant = datetime(2026, 12, 31, 20, 0, tzinfo=timezone.utc)
        self.assertEqual(company_year(self.company, instant), 2027)
        self.company.business_country = 'RU'
        self.assertEqual(company_year(self.company, instant), 2026)
        self.make(SupplierOrder)
        self.company = Company.objects.create(name='Second', business_country='KZ')
        self.assertEqual(self.make(SupplierOrder).order_number, '1')
