from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from customer_orders.models import (
    CustomerOrder,
    CustomerOrderChangeLog,
    CustomerOrderItem,
    CustomerOrderStatus,
)
from products.models import CompanySettings, Product
from supplier_orders.models import SupplierOrder, SupplierOrderStatus
from users.models import Company, CustomUser


class CreateSupplierOrdersTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Acme')
        self.company.apply_country_defaults('KZ')
        self.company.china_warehouse_address = 'China warehouse, Guangzhou'
        self.company.save(update_fields=[
            'business_country',
            'base_currency_code',
            'base_currency_symbol',
            'locale_code',
            'china_warehouse_address',
        ])
        CompanySettings.objects.create(
            company=self.company,
            cny_to_local_rate=Decimal('10.000000'),
            usd_to_local_rate=Decimal('500.000000'),
        )
        self.other_company = Company.objects.create(name='Other')
        self.user = CustomUser.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='pass',
            company=self.company,
            is_company_admin=True,
        )
        self.other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass',
            company=self.other_company,
            is_company_admin=True,
        )
        self.client.force_authenticate(self.user)

        self.customer_status = CustomerOrderStatus.objects.create(
            company=self.company,
            name='New',
            color='#008000',
        )
        self.supplier_status = SupplierOrderStatus.objects.create(
            company=self.company,
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
            company=self.company,
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
        self.assertEqual(order_a.shipping_address, 'China warehouse, Guangzhou')
        self.assertEqual(order_a.shipping_code, 'SHIP-1')
        self.assertEqual(order_a.items.count(), 1)
        self.assertEqual(order_a.items.first().product, self.product_a)
        self.assertEqual(order_a.items.first().quantity, Decimal('2.00'))
        self.assertEqual(order_a.amount_cny, Decimal('20.00'))

        self.assertEqual(order_b.items.count(), 1)
        self.assertEqual(order_b.items.first().product, self.product_b)
        self.assertEqual(order_b.items.first().quantity, Decimal('3.00'))
        self.assertEqual(order_b.amount_cny, Decimal('45.00'))

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
        self.assertEqual(order_a.amount_cny, Decimal('64.00'))

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
        self.order.discount_pct = Decimal('0.1000')
        self.order.save(update_fields=['discount_pct'])
        self.client.post(f'/api/customer-order/{self.order.id}/create-supplier-orders/')

        response = self.client.get(
            f'/api/customer-order/{self.order.id}/related-documents/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['root']['doc_type'], 'customer_order')
        self.assertEqual(response.data['root']['total_amount'], '117.00')
        self.assertEqual(response.data['root']['amount_company_currency'], '117.00')
        self.assertEqual(response.data['root']['company_currency_code'], 'KZT')
        self.assertEqual(response.data['root']['company_currency_symbol'], '₸')
        self.assertEqual(len(response.data['children']), 2)
        child = response.data['children'][0]
        self.assertEqual(child['currency_original'], 'CNY')
        self.assertEqual(child['company_currency_code'], 'KZT')
        self.assertIn('amount_company_currency', child)
        totals_by_supplier = {
            child['supplier_name']: child
            for child in response.data['children']
        }
        self.assertEqual(totals_by_supplier['Supplier A']['amount_original'], '20.00')
        self.assertEqual(totals_by_supplier['Supplier A']['amount_company_currency'], '200.00')
        self.assertEqual(totals_by_supplier['Supplier B']['amount_original'], '45.00')
        self.assertEqual(totals_by_supplier['Supplier B']['amount_company_currency'], '450.00')
        self.assertEqual(
            {child['supplier_name'] for child in response.data['children']},
            {'Supplier A', 'Supplier B'},
        )

    def test_customer_order_detail_returns_discount_totals(self):
        self.order.discount_pct = Decimal('0.1000')
        self.order.save(update_fields=['discount_pct'])
        item_b = CustomerOrderItem.objects.get(product=self.product_b)
        item_b.discount_pct = Decimal('0.2000')
        item_b.save(update_fields=['discount_pct'])

        response = self.client.get(f'/api/customer-order/{self.order.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subtotal_before_order_discount'], Decimal('112.00'))
        self.assertEqual(response.data['order_discount_amount'], Decimal('11.20'))
        self.assertEqual(response.data['total_after_discount'], Decimal('100.80'))

    def test_order_discount_is_blocked_when_line_discount_exists(self):
        item = CustomerOrderItem.objects.get(product=self.product_a)
        item.discount_pct = Decimal('0.1000')
        item.save(update_fields=['discount_pct'])

        response = self.client.patch(f'/api/customer-order/{self.order.id}/', {
            'customer_id': self.customer.id,
            'discount_pct': '0.0500',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('discount_pct', response.data)

    def test_line_discount_can_be_saved_after_order_discount_is_cleared(self):
        self.order.discount_pct = Decimal('0.1000')
        self.order.save(update_fields=['discount_pct'])
        item = CustomerOrderItem.objects.get(product=self.product_a)

        order_response = self.client.patch(f'/api/customer-order/{self.order.id}/', {
            'customer_id': self.customer.id,
            'discount_pct': '0.0000',
        })
        item_response = self.client.patch(f'/api/customer-order-items/{item.id}/', {
            'order': self.order.id,
            'product_id': self.product_a.id,
            'quantity': item.quantity,
            'discount_pct': '0.2000',
        })

        self.assertEqual(order_response.status_code, status.HTTP_200_OK)
        self.assertEqual(item_response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.discount_pct, Decimal('0.2000'))

    def test_order_discount_can_be_saved_after_line_discount_is_cleared(self):
        item = CustomerOrderItem.objects.get(product=self.product_a)
        item.discount_pct = Decimal('0.2000')
        item.save(update_fields=['discount_pct'])

        item_response = self.client.patch(f'/api/customer-order-items/{item.id}/', {
            'order': self.order.id,
            'product_id': self.product_a.id,
            'quantity': item.quantity,
            'discount_pct': '0.0000',
        })
        order_response = self.client.patch(f'/api/customer-order/{self.order.id}/', {
            'customer_id': self.customer.id,
            'discount_pct': '0.1000',
        })

        self.assertEqual(item_response.status_code, status.HTTP_200_OK)
        self.assertEqual(order_response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.discount_pct, Decimal('0.1000'))

    def test_supplier_order_related_documents_returns_sibling_supplier_orders(self):
        self.client.post(f'/api/customer-order/{self.order.id}/create-supplier-orders/')
        supplier_order = SupplierOrder.objects.get(supplier=self.supplier_a)

        response = self.client.get(
            f'/api/supplier-order/{supplier_order.id}/related-documents/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['root']['doc_type'], 'customer_order')
        self.assertEqual(response.data['root']['id'], self.order.id)
        self.assertEqual(len(response.data['children']), 2)
        self.assertEqual(
            {child['supplier_name'] for child in response.data['children']},
            {'Supplier A', 'Supplier B'},
        )

    def test_item_sale_price_is_snapshotted_and_used_after_product_price_changes(self):
        item = CustomerOrderItem.objects.get(product=self.product_a)
        self.assertEqual(item.unit_sale_price, Decimal('20.00'))

        self.product_a.sale_price = Decimal('99.00')
        self.product_a.save(update_fields=['sale_price'])

        response = self.client.get(f'/api/customer-order/{self.order.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item_data = next(row for row in response.data['items'] if row['id'] == item.id)
        self.assertEqual(item_data['unit_sale_price'], '20.00')
        self.assertEqual(item_data['line_total_before_discount'], Decimal('40.00'))
        self.assertEqual(response.data['subtotal_before_order_discount'], Decimal('130.00'))

    def test_item_sale_price_can_be_changed_and_is_logged(self):
        item = CustomerOrderItem.objects.get(product=self.product_a)

        response = self.client.patch(
            f'/api/customer-order-items/{item.id}/',
            {'unit_sale_price': '17.25'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.unit_sale_price, Decimal('17.25'))
        log = CustomerOrderChangeLog.objects.get(
            customer_order=self.order,
            field_name='item_unit_sale_price',
        )
        self.assertEqual(log.old_value, 'A-001: 20.00')
        self.assertEqual(log.new_value, 'A-001: 17.25')
        self.assertEqual(log.changed_by, self.user)

    def test_item_sale_price_cannot_be_negative(self):
        item = CustomerOrderItem.objects.get(product=self.product_a)

        response = self.client.patch(
            f'/api/customer-order-items/{item.id}/',
            {'unit_sale_price': '-0.01'},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('unit_sale_price', response.data)
        item.refresh_from_db()
        self.assertEqual(item.unit_sale_price, Decimal('20.00'))

    def test_company_scope_blocks_other_company_user(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.post(
            f'/api/customer-order/{self.order.id}/create-supplier-orders/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(SupplierOrder.objects.count(), 0)
