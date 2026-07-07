from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from products.models import Product
from supplier_orders.models import SupplierOrder, SupplierOrderStatus
from users.models import Company, CustomUser


class CreateSupplierOrdersTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Acme')
        self.other_company = Company.objects.create(name='Other')
        self.user = CustomUser.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='pass',
            company=self.company,
        )
        self.other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass',
            company=self.other_company,
        )
        self.client.force_authenticate(self.user)

        self.customer_status = CustomerOrderStatus.objects.create(
            name='New',
            color='#008000',
        )
        self.supplier_status = SupplierOrderStatus.objects.create(
            name='Waiting for Invoice',
            color='#28a745',
        )
        self.customer = Counterparty.objects.create(
            company=self.company,
            name='Customer',
            type='local',
            is_customer=True,
        )
        self.supplier_a = Counterparty.objects.create(
            company=self.company,
            name='Supplier A',
            type='china',
            is_supplier=True,
        )
        self.supplier_b = Counterparty.objects.create(
            company=self.company,
            name='Supplier B',
            type='china',
            is_supplier=True,
        )
        self.product_a = Product.objects.create(
            name='Product A',
            sku='A-001',
            supplier=self.supplier_a,
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('20.00'),
        )
        self.product_b = Product.objects.create(
            name='Product B',
            sku='B-001',
            supplier=self.supplier_b,
            purchase_price=Decimal('15.00'),
            sale_price=Decimal('30.00'),
        )
        self.order = CustomerOrder.objects.create(
            status=self.customer_status,
            customer=self.customer,
            planned_receipt_date='2026-06-01',
            shipping_address='Warehouse 1',
            shipping_code='SHIP-1',
            created_by=self.user,
            updated_by=self.user,
        )
        CustomerOrderItem.objects.create(
            order=self.order,
            product=self.product_a,
            quantity=Decimal('2.00'),
            comment='A comment',
        )
        CustomerOrderItem.objects.create(
            order=self.order,
            product=self.product_b,
            quantity=Decimal('3.00'),
            comment='B comment',
        )

    def test_create_supplier_orders_groups_items_by_supplier(self):
        response = self.client.post(
            f'/api/customer-order/{self.order.id}/create-supplier-orders/'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(SupplierOrder.objects.count(), 2)

        order_a = SupplierOrder.objects.get(supplier=self.supplier_a)
        order_b = SupplierOrder.objects.get(supplier=self.supplier_b)

        self.assertEqual(order_a.customer_order, self.order)
        self.assertEqual(order_a.customer, self.customer)
        self.assertEqual(order_a.status, self.supplier_status)
        self.assertEqual(order_a.shipping_address, 'Warehouse 1')
        self.assertEqual(order_a.shipping_code, 'SHIP-1')
        self.assertEqual(order_a.items.count(), 1)
        self.assertEqual(order_a.items.first().product, self.product_a)
        self.assertEqual(order_a.items.first().quantity, Decimal('2.00'))

        self.assertEqual(order_b.items.count(), 1)
        self.assertEqual(order_b.items.first().product, self.product_b)
        self.assertEqual(order_b.items.first().quantity, Decimal('3.00'))

    def test_create_supplier_orders_updates_existing_supplier_order(self):
        self.client.post(f'/api/customer-order/{self.order.id}/create-supplier-orders/')
        product_a2 = Product.objects.create(
            name='Product A2',
            sku='A-002',
            supplier=self.supplier_a,
            purchase_price=Decimal('11.00'),
            sale_price=Decimal('22.00'),
        )
        CustomerOrderItem.objects.create(
            order=self.order,
            product=product_a2,
            quantity=Decimal('4.00'),
            comment='A2 comment',
        )

        response = self.client.post(
            f'/api/customer-order/{self.order.id}/create-supplier-orders/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SupplierOrder.objects.count(), 2)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['updated']), 1)

        order_a = SupplierOrder.objects.get(supplier=self.supplier_a)
        self.assertEqual(order_a.items.count(), 2)
        self.assertTrue(order_a.items.filter(product=product_a2, quantity=Decimal('4.00')).exists())

    def test_create_supplier_orders_creates_new_supplier_order_for_new_supplier(self):
        self.client.post(f'/api/customer-order/{self.order.id}/create-supplier-orders/')
        supplier_c = Counterparty.objects.create(
            company=self.company,
            name='Supplier C',
            type='china',
            is_supplier=True,
        )
        product_c = Product.objects.create(
            name='Product C',
            sku='C-001',
            supplier=supplier_c,
            purchase_price=Decimal('12.00'),
            sale_price=Decimal('24.00'),
        )
        CustomerOrderItem.objects.create(
            order=self.order,
            product=product_c,
            quantity=Decimal('5.00'),
            comment='C comment',
        )

        response = self.client.post(
            f'/api/customer-order/{self.order.id}/create-supplier-orders/'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupplierOrder.objects.count(), 3)
        self.assertEqual(response.data['count'], 1)
        order_c = SupplierOrder.objects.get(supplier=supplier_c)
        self.assertEqual(order_c.customer_order, self.order)
        self.assertEqual(order_c.items.first().product, product_c)

    def test_related_documents_returns_root_and_children(self):
        self.client.post(f'/api/customer-order/{self.order.id}/create-supplier-orders/')

        response = self.client.get(
            f'/api/customer-order/{self.order.id}/related-documents/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['root']['doc_type'], 'customer_order')
        self.assertEqual(response.data['root']['total_amount'], '130.00')
        self.assertEqual(len(response.data['children']), 2)
        self.assertEqual(
            {child['supplier_name'] for child in response.data['children']},
            {'Supplier A', 'Supplier B'},
        )

    def test_company_scope_blocks_other_company_user(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.post(
            f'/api/customer-order/{self.order.id}/create-supplier-orders/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(SupplierOrder.objects.count(), 0)
