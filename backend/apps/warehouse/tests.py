from decimal import Decimal
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from products.models import CompanySettings, Product, ProductCategory, Unit
from supplier_orders.models import SupplierOrder, SupplierOrderItem, SupplierOrderStatus
from users.models import Company
from warehouse.models import StockMovement, WarehouseStock
from warehouse.services import sync_customer_order, sync_supplier_order


class WarehouseSyncTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Warehouse Co')
        self.other_company = Company.objects.create(name='Other Co')
        self.user = User.objects.create_user(
            username='warehouse-user',
            email='warehouse@example.com',
            password='password123',
            company=self.company,
            is_email_verified=True,
        )
        self.other_user = User.objects.create_user(
            username='other-warehouse-user',
            email='other-warehouse@example.com',
            password='password123',
            company=self.other_company,
            is_email_verified=True,
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
            name='Stock Product',
            sku='STOCK-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
            is_stock_item=True,
        )
        self.non_stock_product = Product.objects.create(
            company=self.company,
            name='Regular Product',
            sku='REG-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
            is_stock_item=False,
        )
        self.supplier_status = SupplierOrderStatus.objects.create(
            company=self.company,
            name='Waiting',
        )
        self.received_status = SupplierOrderStatus.objects.create(
            company=self.company,
            name='Received',
        )
        self.cancelled_supplier_status = SupplierOrderStatus.objects.create(
            company=self.company,
            name='Cancelled',
        )
        self.customer_status = CustomerOrderStatus.objects.create(
            company=self.company,
            name='New',
        )
        self.shipped_status = CustomerOrderStatus.objects.create(
            company=self.company,
            name='Shipped',
        )
        self.completed_status = CustomerOrderStatus.objects.create(
            company=self.company,
            name='Completed',
        )
        self.cancelled_customer_status = CustomerOrderStatus.objects.create(
            company=self.company,
            name='Cancelled',
        )

    def test_supplier_order_creates_expected_stock_for_stock_items_only(self):
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.supplier_status,
        )
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('10.00'))
        SupplierOrderItem.objects.create(order=order, product=self.non_stock_product, quantity=Decimal('5.00'))

        sync_supplier_order(order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_expected, Decimal('10.00'))
        self.assertEqual(stock.quantity_on_hand, Decimal('0.00'))
        self.assertFalse(WarehouseStock.objects.filter(product=self.non_stock_product).exists())

    def test_supplier_received_status_moves_quantity_to_on_hand(self):
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('7.00'))

        sync_supplier_order(order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('7.00'))
        self.assertEqual(stock.quantity_expected, Decimal('0.00'))

    def test_supplier_delivered_status_stays_expected(self):
        delivered_status = SupplierOrderStatus.objects.create(
            company=self.company,
            name='Delivered',
        )
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=delivered_status,
        )
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('7.00'))

        sync_supplier_order(order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('0.00'))
        self.assertEqual(stock.quantity_expected, Decimal('7.00'))

    def test_supplier_cancelled_status_removes_expected_stock(self):
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.supplier_status,
        )
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('9.00'))
        sync_supplier_order(order, self.user)

        order.status = self.cancelled_supplier_status
        order.save(update_fields=['status'])
        sync_supplier_order(order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('0.00'))
        self.assertEqual(stock.quantity_expected, Decimal('0.00'))
        self.assertFalse(StockMovement.objects.filter(product=self.product, source_type='supplier_order', source_id=order.id).exists())

    def test_customer_order_reserves_then_ships_stock(self):
        supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(order=supplier_order, product=self.product, quantity=Decimal('12.00'))
        sync_supplier_order(supplier_order, self.user)

        customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        CustomerOrderItem.objects.create(order=customer_order, product=self.product, quantity=Decimal('4.00'))
        sync_customer_order(customer_order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('12.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('4.00'))
        self.assertEqual(stock.quantity_available, Decimal('8.00'))

        customer_order.status = self.shipped_status
        customer_order.save(update_fields=['status'])
        sync_customer_order(customer_order, self.user)

        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, Decimal('8.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('0.00'))
        self.assertEqual(stock.quantity_available, Decimal('8.00'))

    def test_customer_completed_status_ships_stock(self):
        supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(order=supplier_order, product=self.product, quantity=Decimal('12.00'))
        sync_supplier_order(supplier_order, self.user)

        customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.completed_status,
        )
        CustomerOrderItem.objects.create(order=customer_order, product=self.product, quantity=Decimal('4.00'))

        sync_customer_order(customer_order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('8.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('0.00'))
        self.assertEqual(stock.quantity_available, Decimal('8.00'))

    def test_customer_cancelled_status_removes_reserved_stock(self):
        supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(order=supplier_order, product=self.product, quantity=Decimal('12.00'))
        sync_supplier_order(supplier_order, self.user)

        customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        CustomerOrderItem.objects.create(order=customer_order, product=self.product, quantity=Decimal('4.00'))
        sync_customer_order(customer_order, self.user)

        customer_order.status = self.cancelled_customer_status
        customer_order.save(update_fields=['status'])
        sync_customer_order(customer_order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('12.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('0.00'))
        self.assertEqual(stock.quantity_available, Decimal('12.00'))
        self.assertFalse(StockMovement.objects.filter(product=self.product, source_type='customer_order', source_id=customer_order.id).exists())

    def test_sync_is_idempotent_for_same_order(self):
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.supplier_status,
        )
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('3.00'))

        sync_supplier_order(order, self.user)
        sync_supplier_order(order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_expected, Decimal('3.00'))
        self.assertEqual(StockMovement.objects.filter(product=self.product).count(), 1)

    def test_sync_preserves_movement_date_when_status_does_not_change(self):
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=Decimal('3.00'),
        )
        sync_supplier_order(order, self.user)
        movement = StockMovement.objects.get(product=self.product)
        original_date = timezone.now() - timedelta(days=5)
        StockMovement.objects.filter(pk=movement.pk).update(created_at=original_date)

        sync_supplier_order(order, self.user)

        movement.refresh_from_db()
        self.assertEqual(movement.created_at, original_date)

    def test_supplier_order_captures_rate_currency_and_item_price(self):
        self.company.base_currency_code = 'KZT'
        self.company.base_currency_symbol = '₸'
        self.company.save(update_fields=['base_currency_code', 'base_currency_symbol'])
        settings = CompanySettings.objects.create(
            company=self.company,
            cny_to_local_rate=Decimal('70.00'),
        )
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.supplier_status,
        )
        item = SupplierOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=Decimal('2.00'),
        )

        settings.cny_to_local_rate = Decimal('75.00')
        settings.save(update_fields=['cny_to_local_rate'])
        self.product.purchase_price = Decimal('15.00')
        self.product.save(update_fields=['purchase_price'])
        order.refresh_from_db()
        item.refresh_from_db()

        self.assertEqual(order.cny_to_local_rate, Decimal('70.00'))
        self.assertEqual(order.company_currency_code, 'KZT')
        self.assertEqual(order.company_currency_symbol, '₸')
        self.assertEqual(item.unit_price_cny, Decimal('10.00'))

    def test_warehouse_api_is_company_scoped(self):
        WarehouseStock.objects.create(
            company=self.company,
            product=self.product,
            quantity_on_hand=Decimal('5.00'),
        )
        other_supplier = Counterparty.objects.create(
            company=self.other_company,
            name='Other Supplier',
            type='china',
            is_supplier=True,
        )
        other_product = Product.objects.create(
            company=self.other_company,
            name='Other Product',
            sku='OTHER-001',
            supplier=other_supplier,
            is_stock_item=True,
        )
        WarehouseStock.objects.create(
            company=self.other_company,
            product=other_product,
            quantity_on_hand=Decimal('9.00'),
        )

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-stocks/')

        self.assertEqual(response.status_code, 200)
        products = [item['product']['sku'] for item in response.data]
        self.assertEqual(products, ['STOCK-001'])

    def test_warehouse_api_can_filter_by_supplier(self):
        WarehouseStock.objects.create(
            company=self.company,
            product=self.product,
            quantity_on_hand=Decimal('5.00'),
        )
        other_supplier = Counterparty.objects.create(
            company=self.company,
            name='Second Supplier',
            type='china',
            is_supplier=True,
        )
        other_product = Product.objects.create(
            company=self.company,
            name='Second Stock Product',
            sku='STOCK-002',
            supplier=other_supplier,
            is_stock_item=True,
        )
        WarehouseStock.objects.create(
            company=self.company,
            product=other_product,
            quantity_on_hand=Decimal('3.00'),
        )

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-stocks/', {'supplier': self.supplier.id})

        self.assertEqual(response.status_code, 200)
        products = [item['product']['sku'] for item in response.data]
        self.assertEqual(products, ['STOCK-001'])

    def test_warehouse_report_exports_filtered_supplier_items(self):
        category = ProductCategory.objects.create(company=self.company, name='Textile')
        unit = Unit.objects.create(company=self.company, name='m')
        self.product.category = category
        self.product.unit = unit
        self.product.save(update_fields=['category', 'unit'])
        CompanySettings.objects.create(
            company=self.company,
            cny_to_local_rate=Decimal('70.00'),
        )
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=Decimal('4.00'),
            unit='m',
        )
        sync_supplier_order(order, self.user)

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-report/export/', {
            'supplier': self.supplier.id,
            'category': category.id,
            'search': 'STOCK-001',
            'date_from': timezone.localdate(),
            'date_to': timezone.localdate(),
        })

        self.assertEqual(response.status_code, 200)
        content = b''.join(response.streaming_content)
        workbook = load_workbook(BytesIO(content), data_only=False)
        self.assertEqual(workbook.sheetnames, ['Warehouse report'])
        sheet = workbook['Warehouse report']
        self.assertEqual(sheet.max_row, 2)
        self.assertEqual(sheet['A2'].value, order.order_number)
        self.assertEqual(sheet['B2'].value, 'STOCK-001')
        self.assertEqual(sheet['D2'].value, 'Supplier')
        self.assertEqual(sheet['H2'].value, 'Received')
        self.assertEqual(sheet['I2'].value, 4)
        self.assertEqual(sheet['K2'].value, 10)
        self.assertEqual(sheet['L2'].value, '=I2*K2')
        self.assertEqual(sheet['M2'].value, 70)
        self.assertEqual(sheet['N2'].value, '=L2*M2')
        self.assertEqual(sheet['O2'].value, 'KZT')

    def test_warehouse_report_rejects_reversed_period(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-report/export/', {
            'date_from': '2026-08-25',
            'date_to': '2026-08-01',
        })

        self.assertEqual(response.status_code, 400)
