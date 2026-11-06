from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from products.models import Product, ProductChangeLog
from supplier_orders.models import SupplierOrder, SupplierOrderItem, SupplierOrderStatus
from users.access import ensure_default_access_structure
from users.models import Company, CustomUser


class FinancialReportAccessTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Access report company', language_code='en')
        roles = ensure_default_access_structure(self.company)
        self.users = {}
        for key, role_name in (
            ('purchasing', 'WED manager'),
            ('sales', 'Sales manager'),
            ('finance', 'Financial analyst'),
            ('warehouse', 'Warehouse manager'),
        ):
            self.users[key] = CustomUser.objects.create_user(
                username=f'access-{key}',
                email=f'access-{key}@example.com',
                password='pass',
                company=self.company,
                role='manager',
                access_role=roles[role_name],
            )

        self.supplier = Counterparty.objects.create(
            company=self.company,
            name='Supplier',
            type='china',
            is_supplier=True,
        )
        self.customer = Counterparty.objects.create(
            company=self.company,
            name='Customer',
            type='local',
            is_customer=True,
        )
        self.product = Product.objects.create(
            company=self.company,
            supplier=self.supplier,
            name='Sensitive product',
            sku='SEC-001',
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('25.00'),
        )
        self.supplier_status = SupplierOrderStatus.objects.create(
            company=self.company,
            name='New supplier order',
        )
        self.customer_status = CustomerOrderStatus.objects.create(
            company=self.company,
            name='New customer order',
        )
        self.customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        CustomerOrderItem.objects.create(
            order=self.customer_order,
            product=self.product,
            quantity=Decimal('2.00'),
            unit_sale_price=Decimal('25.00'),
        )
        self.supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            customer=self.customer,
            customer_order=self.customer_order,
            status=self.supplier_status,
        )
        SupplierOrderItem.objects.create(
            order=self.supplier_order,
            product=self.product,
            quantity=Decimal('2.00'),
            unit_price_cny=Decimal('10.00'),
        )

    def authenticate(self, key):
        self.client.force_authenticate(self.users[key])

    def test_product_prices_and_settings_follow_functional_role(self):
        for role in ('sales', 'purchasing', 'warehouse', 'finance'):
            self.authenticate(role)
            response = self.client.get(f'/api/products/{self.product.pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual('purchase_price' in response.data, role in ('purchasing', 'finance'))
            self.assertEqual('cost_price' in response.data, role in ('purchasing', 'finance'))
            self.assertEqual('sale_price' in response.data, role in ('sales', 'finance'))
            self.assertNotIn('applied_markup_pct', response.data)
            settings = self.client.get('/api/settings/').data[0]
            self.assertNotIn('margin_pct', settings)
            self.assertNotIn('cny_to_local_rate', settings)

    def workbook_headers(self, response):
        workbook = load_workbook(BytesIO(b''.join(response.streaming_content)), data_only=False)
        sheet = workbook.active
        header_row = next(
            row[0].row
            for row in sheet.iter_rows()
            if row[0].value in ('Order #', 'Заказ №')
        )
        return [cell.value for cell in sheet[header_row] if cell.value is not None]

    def test_owner_analytics_requires_financial_report_permission(self):
        self.authenticate('purchasing')
        self.assertEqual(self.client.get('/api/supplier-order/analytics/').status_code, 403)

        self.authenticate('finance')
        response = self.client.get('/api/supplier-order/analytics/')
        self.assertEqual(response.status_code, 200)

    def test_order_exports_keep_operational_columns_but_redact_prices(self):
        self.authenticate('warehouse')
        supplier_response = self.client.get('/api/supplier-order/export/')
        self.assertEqual(supplier_response.status_code, 200)
        supplier_headers = self.workbook_headers(supplier_response)
        self.assertIn('Quantity', supplier_headers)
        self.assertNotIn('Unit price, CNY', supplier_headers)
        self.assertNotIn('Total, CNY', supplier_headers)

        self.authenticate('purchasing')
        supplier_response = self.client.get('/api/supplier-order/export/')
        self.assertIn('Unit price, CNY', self.workbook_headers(supplier_response))

        self.authenticate('purchasing')
        customer_response = self.client.get('/api/customer-order/export/')
        self.assertEqual(customer_response.status_code, 200)
        self.assertNotIn('Unit price, local', self.workbook_headers(customer_response))

        self.authenticate('sales')
        customer_response = self.client.get('/api/customer-order/export/')
        self.assertIn('Unit price, local', self.workbook_headers(customer_response))

    def test_functional_roles_cannot_open_unrelated_order_section(self):
        self.authenticate('sales')
        self.assertEqual(self.client.get('/api/supplier-order/').status_code, 403)

        self.authenticate('purchasing')
        self.assertEqual(self.client.get('/api/customer-order/').status_code, 200)
        self.assertEqual(self.client.post('/api/customer-order/', {}).status_code, 403)

    def test_related_document_cards_do_not_leak_unavailable_amounts(self):
        self.authenticate('sales')
        response = self.client.get(
            f'/api/customer-order/{self.customer_order.pk}/related-documents/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_amount', response.data['root'])
        self.assertEqual(response.data['children'], [])

        self.authenticate('purchasing')
        response = self.client.get(
            f'/api/supplier-order/{self.supplier_order.pk}/related-documents/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('total_amount', response.data['root'])
        self.assertIn('amount_original', response.data['children'][0])

    def test_history_hides_prices_without_the_corresponding_permission(self):
        ProductChangeLog.objects.create(
            product=self.product,
            field_name='purchase_price',
            old_value='9.00',
            new_value='10.00',
        )
        ProductChangeLog.objects.create(
            product=self.product,
            field_name='sale_price',
            old_value='20.00',
            new_value='25.00',
        )
        ProductChangeLog.objects.create(
            product=self.product,
            field_name='name',
            old_value='Old',
            new_value='Sensitive product',
        )

        self.authenticate('warehouse')
        response = self.client.get(f'/api/products/{self.product.pk}/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item['field_name'] for item in response.data}, {'name'})

        self.authenticate('purchasing')
        response = self.client.get(f'/api/products/{self.product.pk}/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item['field_name'] for item in response.data},
            {'name', 'purchase_price'},
        )

    def test_warehouse_reports_redact_financial_metrics_without_price_access(self):
        self.authenticate('warehouse')
        export_response = self.client.get('/api/warehouse-report/export/')
        self.assertEqual(export_response.status_code, 200)
        workbook = load_workbook(
            BytesIO(b''.join(export_response.streaming_content)),
            data_only=False,
        )
        headers = [cell.value for cell in workbook.active[6] if cell.value is not None]
        self.assertIn('Quantity', headers)
        self.assertNotIn('Unit price, CNY', headers)

        summary = self.client.get('/api/warehouse-report/summary/')
        self.assertEqual(summary.status_code, 200)
        self.assertNotIn('total_cny', summary.data['totals'])
        self.assertNotIn('total_local', summary.data['totals'])
        self.assertEqual(
            self.client.get('/api/warehouse-report/summary/', {'metric': 'total_cny'}).status_code,
            403,
        )

        self.authenticate('purchasing')
        export_response = self.client.get('/api/warehouse-report/export/')
        workbook = load_workbook(
            BytesIO(b''.join(export_response.streaming_content)),
            data_only=False,
        )
        headers = [cell.value for cell in workbook.active[6] if cell.value is not None]
        self.assertIn('Unit price, CNY', headers)

