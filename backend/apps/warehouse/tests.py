from decimal import Decimal
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from customer_orders.services.create_supplier_orders import create_supplier_orders_for_customer_order
from products.models import CompanySettings, Product, ProductCategory, Unit
from supplier_orders.models import SupplierOrder, SupplierOrderItem, SupplierOrderStatus
from users.models import Company
from warehouse.models import StockAlert, StockControlSnapshot, StockMovement, WarehouseStock
from warehouse.services import recalculate_product_stock, sync_critical_stock_alert, sync_customer_order, sync_supplier_order
from warehouse.stock_control import ensure_due_stock_control_snapshot, stock_control_rows


def paginated_results(response):
    return response.data.get('results', response.data)


class StockControlDemoCommandTests(APITestCase):
    @override_settings(DEBUG=True)
    def test_command_creates_repeatable_dated_demo_history(self):
        company = Company.objects.create(name='Stock Demo Co')

        call_command(
            'seed_stock_control_demo',
            company=company.name,
            reset=True,
            stdout=StringIO(),
        )

        products = Product.objects.filter(company=company, description='[stock-control-demo]')
        self.assertEqual(products.count(), 7)
        self.assertEqual(
            StockMovement.objects.filter(company=company, source_type='stock_control_demo').count(),
            12,
        )
        rows = {row['sku']: row for row in stock_control_rows(company)}
        self.assertEqual(rows['2099-17']['status'], 'out_of_stock')
        self.assertEqual(rows['2099-21']['status'], 'below_minimum')
        self.assertEqual(rows['DCD16-91']['status'], 'requires_order')
        self.assertEqual(rows['IBG5036-92']['status'], 'supply_expected')
        self.assertEqual(rows['5819-91']['forecast_quality'], 'insufficient')
        self.assertEqual(rows['IBG5036-93']['forecast_quality'], 'sufficient')

        call_command(
            'seed_stock_control_demo',
            company=company.name,
            clear=True,
            stdout=StringIO(),
        )
        self.assertFalse(
            Product.objects.filter(company=company, description='[stock-control-demo]').exists()
        )


class WarehouseSyncTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Warehouse Co', language_code='en')
        self.other_company = Company.objects.create(name='Other Co', language_code='en')
        self.user = User.objects.create_user(
            username='warehouse-user',
            email='warehouse@example.com',
            password='password123',
            company=self.company,
            is_email_verified=True,
            is_company_admin=True,
        )
        self.other_user = User.objects.create_user(
            username='other-warehouse-user',
            email='other-warehouse@example.com',
            password='password123',
            company=self.other_company,
            is_email_verified=True,
            is_company_admin=True,
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

    def test_supplier_defect_is_kept_separate_from_available_stock(self):
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=Decimal('50.00'),
            defective_quantity=Decimal('10.00'),
        )

        sync_supplier_order(order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('40.00'))
        self.assertEqual(stock.quantity_available, Decimal('40.00'))
        self.assertEqual(stock.quantity_defective, Decimal('10.00'))
        self.assertEqual(stock.quantity_physical, Decimal('50.00'))

    def test_defect_can_be_released_and_written_off(self):
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=Decimal('50.00'),
            defective_quantity=Decimal('10.00'),
        )
        sync_supplier_order(order, self.user)
        stock = WarehouseStock.objects.get(product=self.product)
        self.client.force_authenticate(self.user)

        released = self.client.post(
            f'/api/warehouse-stocks/{stock.id}/operation/',
            {'action': 'release_defect', 'quantity': '6.00'},
            format='json',
        )
        self.assertEqual(released.status_code, 200)
        self.assertEqual(released.data['quantity_available'], '46.00')
        self.assertEqual(released.data['quantity_defective'], '4.00')
        self.assertEqual(released.data['quantity_physical'], '50.00')

        written_off = self.client.post(
            f'/api/warehouse-stocks/{stock.id}/operation/',
            {'action': 'write_off_defect', 'quantity': '4.00'},
            format='json',
        )
        self.assertEqual(written_off.status_code, 200)
        self.assertEqual(written_off.data['quantity_defective'], '0.00')
        self.assertEqual(written_off.data['quantity_physical'], '46.00')

    def test_available_stock_write_off_records_reason(self):
        StockMovement.objects.create(
            company=self.company,
            product=self.product,
            movement_type=StockMovement.TYPE_PURCHASE_RECEIVED,
            quantity=Decimal('20.00'),
            source_key='test:available-stock',
        )
        stock = recalculate_product_stock(self.product)
        self.client.force_authenticate(self.user)

        response = self.client.post(
            f'/api/warehouse-stocks/{stock.id}/operation/',
            {
                'action': 'write_off_stock',
                'quantity': '3.00',
                'reason': 'marketing',
                'comment': 'Showroom sample',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['quantity_available'], '17.00')
        movement = StockMovement.objects.get(movement_type=StockMovement.TYPE_STOCK_WRITTEN_OFF)
        self.assertIn('marketing', movement.comment)

    def test_supplier_received_status_uses_stable_code_after_renaming(self):
        renamed_received = SupplierOrderStatus.objects.create(
            company=self.company,
            name='Принято на склад',
            translations={'en': 'Accepted into warehouse', 'ru': 'Принято на склад'},
            code='received',
            is_system=True,
        )
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=renamed_received,
        )
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=Decimal('4.00'))

        sync_supplier_order(order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('4.00'))
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

    def test_critical_alert_is_created_once_and_resolved_after_recovery(self):
        self.product.minimum_stock_level = Decimal('5.00')
        self.product.average_monthly_consumption = Decimal('0.00')
        self.product.consumption_calculation_mode = Product.CONSUMPTION_MODE_MANUAL
        self.product.purchase_batch_size = Decimal('10.00')
        self.product.save(update_fields=[
            'minimum_stock_level', 'average_monthly_consumption',
            'consumption_calculation_mode', 'purchase_batch_size',
        ])
        supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=supplier_order,
            product=self.product,
            quantity=Decimal('10.00'),
        )
        sync_supplier_order(supplier_order, self.user)

        customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        CustomerOrderItem.objects.create(
            order=customer_order,
            product=self.product,
            quantity=Decimal('6.00'),
        )
        sync_customer_order(customer_order, self.user)
        sync_customer_order(customer_order, self.user)

        alert = StockAlert.objects.get(product=self.product, resolved_at__isnull=True)
        self.assertEqual(alert.available_quantity, Decimal('4.00'))
        self.assertEqual(
            StockAlert.objects.filter(product=self.product, resolved_at__isnull=True).count(),
            1,
        )
        self.client.force_authenticate(self.user)
        listed = self.client.get('/api/warehouse-stock-alerts/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item['id'] for item in listed.data], [alert.id])
        dismissed = self.client.post(f'/api/warehouse-stock-alerts/{alert.id}/dismiss/')
        self.assertEqual(dismissed.status_code, 200)
        self.assertEqual(self.client.get('/api/warehouse-stock-alerts/').data, [])

        customer_order.status = self.cancelled_customer_status
        customer_order.save(update_fields=['status'])
        sync_customer_order(customer_order, self.user)

        alert.refresh_from_db()
        self.assertIsNotNone(alert.resolved_at)

    def test_available_stock_never_goes_below_zero_when_reserved_before_receipt(self):
        supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.supplier_status,
        )
        SupplierOrderItem.objects.create(order=supplier_order, product=self.product, quantity=Decimal('300.00'))
        sync_supplier_order(supplier_order, self.user)

        customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        CustomerOrderItem.objects.create(order=customer_order, product=self.product, quantity=Decimal('12.60'))
        sync_customer_order(customer_order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('0.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('12.60'))
        self.assertEqual(stock.quantity_expected, Decimal('300.00'))
        self.assertEqual(stock.quantity_available, Decimal('0.00'))

        supplier_order.status = self.received_status
        supplier_order.save(update_fields=['status'])
        sync_supplier_order(supplier_order, self.user)

        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, Decimal('300.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('12.60'))
        self.assertEqual(stock.quantity_expected, Decimal('0.00'))
        self.assertEqual(stock.quantity_available, Decimal('287.40'))

    def test_customer_order_with_linked_supplier_order_does_not_affect_stock(self):
        customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        CustomerOrderItem.objects.create(
            order=customer_order,
            product=self.product,
            quantity=Decimal('12.60'),
            unit='m',
        )
        sync_customer_order(customer_order, self.user)

        stock = WarehouseStock.objects.get(product=self.product)
        self.assertEqual(stock.quantity_on_hand, Decimal('0.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('12.60'))
        self.assertEqual(stock.quantity_expected, Decimal('0.00'))
        self.assertEqual(stock.quantity_available, Decimal('0.00'))

        result = create_supplier_orders_for_customer_order(customer_order, self.user)
        supplier_order = result['created'][0]

        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, Decimal('0.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('0.00'))
        self.assertEqual(stock.quantity_expected, Decimal('0.00'))
        self.assertEqual(stock.quantity_available, Decimal('0.00'))

        supplier_order.status = self.received_status
        supplier_order.save(update_fields=['status'])
        sync_supplier_order(supplier_order, self.user)

        customer_order.status = self.completed_status
        customer_order.save(update_fields=['status'])
        sync_customer_order(customer_order, self.user)

        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, Decimal('0.00'))
        self.assertEqual(stock.quantity_reserved, Decimal('0.00'))
        self.assertEqual(stock.quantity_expected, Decimal('0.00'))
        self.assertEqual(stock.quantity_available, Decimal('0.00'))

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
        products = [item['product']['sku'] for item in paginated_results(response)]
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
        products = [item['product']['sku'] for item in paginated_results(response)]
        self.assertEqual(products, ['STOCK-001'])

    def test_warehouse_api_can_filter_by_supplier_and_category_text(self):
        category = ProductCategory.objects.create(company=self.company, name='Textile')
        self.product.category = category
        self.product.save(update_fields=['category'])
        WarehouseStock.objects.create(
            company=self.company,
            product=self.product,
            quantity_on_hand=Decimal('5.00'),
        )
        other_category = ProductCategory.objects.create(company=self.company, name='Lighting')
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
            category=other_category,
            is_stock_item=True,
        )
        WarehouseStock.objects.create(
            company=self.company,
            product=other_product,
            quantity_on_hand=Decimal('3.00'),
        )

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-stocks/', {
            'supplier_query': 'Supp',
            'category_query': 'Text',
        })

        self.assertEqual(response.status_code, 200)
        products = [item['product']['sku'] for item in paginated_results(response)]
        self.assertEqual(products, ['STOCK-001'])

    def test_warehouse_api_can_filter_by_supplier_order_period(self):
        today_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=today_order,
            product=self.product,
            quantity=Decimal('5.00'),
            unit='m',
        )
        sync_supplier_order(today_order, self.user)

        other_product = Product.objects.create(
            company=self.company,
            name='Old Stock Product',
            sku='OLD-001',
            supplier=self.supplier,
            is_stock_item=True,
        )
        old_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=old_order,
            product=other_product,
            quantity=Decimal('3.00'),
            unit='m',
        )
        SupplierOrder.objects.filter(id=old_order.id).update(
            created_at=timezone.now() - timedelta(days=1)
        )
        old_order.refresh_from_db()
        sync_supplier_order(old_order, self.user)

        linked_customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        linked_supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            customer=self.customer,
            customer_order=linked_customer_order,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=linked_supplier_order,
            product=other_product,
            quantity=Decimal('8.00'),
            unit='m',
        )
        sync_supplier_order(linked_supplier_order, self.user)

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-stocks/', {
            'date_from': timezone.localdate().isoformat(),
            'date_to': timezone.localdate().isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        products = [item['product']['sku'] for item in paginated_results(response)]
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
        self.assertEqual(sheet['A1'].value, 'Warehouse report export')
        self.assertEqual(sheet['A2'].value, 'Generated at')
        self.assertEqual(sheet['A3'].value, 'Active filters')
        self.assertIn('Supplier: Supplier', sheet['B3'].value)
        self.assertIn('Category: Textile', sheet['B3'].value)
        self.assertEqual(sheet['B4'].value, '1 orders; 1 positions; all matching pages')
        self.assertEqual(sheet['A6'].value, 'Order #')
        self.assertEqual(sheet['A7'].value, order.order_number)
        self.assertEqual(sheet['B7'].value, 'STOCK-001')
        self.assertEqual(sheet['D7'].value, 'Supplier')
        self.assertEqual(sheet['H7'].value, 'Received')
        self.assertEqual(sheet['I7'].value, 4)
        self.assertEqual(sheet['K7'].value, 10)
        self.assertEqual(sheet['L7'].value, '=I7*K7')
        self.assertEqual(sheet['L7'].data_type, 'f')
        self.assertEqual(sheet['M7'].value, 70)
        self.assertEqual(sheet['N7'].value, '=L7*M7')
        self.assertEqual(sheet['N7'].data_type, 'f')
        self.assertEqual(sheet['O7'].value, 'KZT')
        totals = {row[0]: row[1] for row in sheet.iter_rows(values_only=True) if row[0]}
        self.assertEqual(totals['Orders count'], 1)
        self.assertEqual(totals['Positions count'], 1)
        self.assertEqual(totals['Total quantity, m'], 4)
        self.assertEqual(totals['Total, CNY'], 40)
        self.assertEqual(totals['Total, KZT'], 2800)
        self.assertIsNone(sheet.auto_filter.ref)
        self.assertIsNone(sheet.freeze_panes)

    def test_warehouse_report_can_export_only_available_items(self):
        available_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=available_order,
            product=self.product,
            quantity=Decimal('4.00'),
            unit='m',
        )
        sync_supplier_order(available_order, self.user)

        fully_reserved_product = Product.objects.create(
            company=self.company,
            name='Fully Reserved Product',
            sku='RESERVED-001',
            supplier=self.supplier,
            purchase_price=Decimal('6.00'),
            is_stock_item=True,
        )
        reserved_supplier_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=reserved_supplier_order,
            product=fully_reserved_product,
            quantity=Decimal('5.00'),
            unit='m',
        )
        sync_supplier_order(reserved_supplier_order, self.user)
        reserved_customer_order = CustomerOrder.objects.create(
            company=self.company,
            customer=self.customer,
            status=self.customer_status,
        )
        CustomerOrderItem.objects.create(
            order=reserved_customer_order,
            product=fully_reserved_product,
            quantity=Decimal('5.00'),
            unit='m',
        )
        sync_customer_order(reserved_customer_order, self.user)

        expected_product = Product.objects.create(
            company=self.company,
            name='Expected Product',
            sku='EXPECTED-001',
            supplier=self.supplier,
            purchase_price=Decimal('5.00'),
            is_stock_item=True,
        )
        expected_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.supplier_status,
        )
        SupplierOrderItem.objects.create(
            order=expected_order,
            product=expected_product,
            quantity=Decimal('10.00'),
            unit='m',
        )
        sync_supplier_order(expected_order, self.user)

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-report/export/', {
            'only_available': '1',
        })

        self.assertEqual(response.status_code, 200)
        content = b''.join(response.streaming_content)
        workbook = load_workbook(BytesIO(content), data_only=False)
        sheet = workbook['Warehouse report']
        header_row = next(row[0].row for row in sheet if row[0].value == 'Order #')
        data_end = next(row[0].row for row in sheet if row[0].value == 'Totals') - 2
        skus = [sheet.cell(row, 2).value for row in range(header_row + 1, data_end + 1)]
        self.assertEqual(skus, ['STOCK-001'])
        self.assertTrue(any(cell.value == 'Totals' for row in sheet for cell in row))

    def test_warehouse_report_can_export_selected_products(self):
        selected_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=selected_order,
            product=self.product,
            quantity=Decimal('4.00'),
            unit='m',
        )
        sync_supplier_order(selected_order, self.user)

        other_product = Product.objects.create(
            company=self.company,
            name='Other Stock Product',
            sku='OTHER-STOCK',
            supplier=self.supplier,
            purchase_price=Decimal('8.00'),
            is_stock_item=True,
        )
        other_order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=other_order,
            product=other_product,
            quantity=Decimal('7.00'),
            unit='m',
        )
        sync_supplier_order(other_order, self.user)

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-report/export/', {
            'product_ids': str(self.product.id),
        })

        self.assertEqual(response.status_code, 200)
        content = b''.join(response.streaming_content)
        workbook = load_workbook(BytesIO(content), data_only=False)
        sheet = workbook['Warehouse report']
        header_row = next(row[0].row for row in sheet if row[0].value == 'Order #')
        data_end = next(row[0].row for row in sheet if row[0].value == 'Totals') - 2
        skus = [sheet.cell(row, 2).value for row in range(header_row + 1, data_end + 1)]
        self.assertEqual(skus, ['STOCK-001'])
        self.assertTrue(any(cell.value == 'Totals' for row in sheet for cell in row))

    def test_warehouse_report_summary_groups_selected_products(self):
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
        SupplierOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=Decimal('6.00'),
            unit='m',
        )
        sync_supplier_order(order, self.user)

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-report/summary/', {
            'product_ids': str(self.product.id),
            'metric': 'quantity',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['limit'], 20)
        self.assertEqual(response.data['items'][0]['sku'], 'STOCK-001')
        self.assertEqual(response.data['items'][0]['quantity'], '10.00')
        self.assertEqual(response.data['items'][0]['total_cny'], '100.00')
        self.assertNotIn('orders_count', response.data['items'][0])
        self.assertNotIn('orders_count', response.data['totals'])
        self.assertEqual(response.data['totals']['products_count'], 1)
        self.assertEqual(response.data['totals']['quantity_totals'], [
            {'unit': 'm', 'quantity': '10.00'},
        ])
        self.assertEqual(response.data['selected_unit'], 'm')

    def test_warehouse_summary_and_export_keep_units_separate(self):
        set_product = Product.objects.create(
            company=self.company,
            name='Sample Set',
            sku='SET-001',
            supplier=self.supplier,
            purchase_price=Decimal('30.00'),
            is_stock_item=True,
        )
        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.received_status,
        )
        SupplierOrderItem.objects.create(
            order=order, product=self.product, quantity=Decimal('4.00'), unit='m',
        )
        SupplierOrderItem.objects.create(
            order=order, product=set_product, quantity=Decimal('3.00'), unit='sets',
        )
        sync_supplier_order(order, self.user)
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/warehouse-report/summary/', {'metric': 'quantity'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['available_units'], ['m', 'sets'])
        self.assertEqual(response.data['selected_unit'], 'm')
        self.assertEqual([item['sku'] for item in response.data['items']], ['STOCK-001'])
        self.assertIsNone(response.data['totals']['quantity'])
        self.assertEqual(response.data['totals']['quantity_totals'], [
            {'unit': 'm', 'quantity': '4.00'},
            {'unit': 'sets', 'quantity': '3.00'},
        ])

        sets_response = self.client.get('/api/warehouse-report/summary/', {
            'metric': 'quantity',
            'unit': 'sets',
        })
        self.assertEqual(sets_response.data['selected_unit'], 'sets')
        self.assertEqual([item['sku'] for item in sets_response.data['items']], ['SET-001'])

        money_response = self.client.get('/api/warehouse-report/summary/', {'metric': 'total_cny'})
        self.assertIsNone(money_response.data['selected_unit'])
        self.assertEqual(
            {item['sku'] for item in money_response.data['items']},
            {'STOCK-001', 'SET-001'},
        )

        export_response = self.client.get('/api/warehouse-report/export/')
        workbook = load_workbook(BytesIO(b''.join(export_response.streaming_content)), data_only=False)
        sheet = workbook['Warehouse report']
        totals = {row[0]: row[1] for row in sheet.iter_rows(values_only=True) if row[0]}
        self.assertEqual(totals['Total quantity, m'], 4)
        self.assertEqual(totals['Total quantity, sets'], 3)
        self.assertNotIn('Total quantity', totals)

    def test_summary_breakdown_tracks_receipt_without_double_counting(self):
        orders = []
        for status, quantity, price, rate in (
            (self.received_status, '4', '10', '2'),
            (self.supplier_status, '6', '20', '3'),
        ):
            self.product.purchase_price = Decimal(price)
            self.product.save()
            order = SupplierOrder.objects.create(
                company=self.company, supplier=self.supplier, status=status,
            )
            order.cny_to_local_rate = Decimal(rate)
            order.save(update_fields=['cny_to_local_rate'])
            SupplierOrderItem.objects.create(
                order=order, product=self.product, quantity=Decimal(quantity),
                unit_price_cny=Decimal(price), unit='m',
            )
            sync_supplier_order(order, self.user)
            orders.append(order)

        self.client.force_authenticate(self.user)
        params = {'product_ids': str(self.product.id), 'metric': 'total_local'}
        response = self.client.get('/api/warehouse-report/summary/', params)
        self.assertEqual(response.status_code, 200)
        item = response.data['items'][0]
        self.assertEqual(item['breakdown']['received'], {
            'quantity': '4.00', 'total_cny': '40.00', 'total_local': '80.00',
        })
        self.assertEqual(item['breakdown']['expected'], {
            'quantity': '6.00', 'total_cny': '120.00', 'total_local': '360.00',
        })
        for metric in ('quantity', 'total_cny', 'total_local'):
            self.assertEqual(
                Decimal(item[metric]),
                sum(Decimal(values[metric]) for values in item['breakdown'].values()),
            )

        orders[1].status = self.received_status
        orders[1].save()
        sync_supplier_order(orders[1], self.user)
        response = self.client.get('/api/warehouse-report/summary/', params)
        self.assertEqual(response.status_code, 200)
        received_item = response.data['items'][0]
        for metric in ('quantity', 'total_cny', 'total_local'):
            self.assertEqual(received_item[metric], item[metric])
            self.assertEqual(received_item['breakdown']['received'][metric], item[metric])
            self.assertEqual(received_item['breakdown']['expected'][metric], '0.00')

    def test_warehouse_report_summary_rejects_more_than_twenty_products(self):
        product_ids = ','.join(str(index) for index in range(1, 22))

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-report/summary/', {
            'product_ids': product_ids,
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Select up to 20 products for the chart.')

    def test_warehouse_report_rejects_reversed_period(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/warehouse-report/export/', {
            'date_from': '2026-08-25',
            'date_to': '2026-08-01',
        })

        self.assertEqual(response.status_code, 400)


class StockControlTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Stock Control Co', language_code='en')
        self.other_company = Company.objects.create(name='Other Stock Control Co', language_code='en')
        self.user = User.objects.create_user(
            username='stock-control-user',
            email='stock-control@example.com',
            password='password123',
            company=self.company,
            is_email_verified=True,
            is_company_admin=True,
        )
        self.other_user = User.objects.create_user(
            username='other-stock-control-user',
            email='other-stock-control@example.com',
            password='password123',
            company=self.other_company,
            is_email_verified=True,
            is_company_admin=True,
        )
        self.supplier = Counterparty.objects.create(
            company=self.company,
            name='BG',
            type='china',
            is_supplier=True,
        )
        self.unit = Unit.objects.create(company=self.company, name='m')
        self.settings = CompanySettings.objects.create(
            company=self.company,
            stock_delivery_lead_days=30,
            stock_timezone='UTC',
            stock_notification_weekday=0,
            stock_notification_time=time(10, 0),
        )

    def create_stock(self, sku, on_hand, reserved, expected, minimum, monthly, batch=None, mode='manual'):
        product = Product.objects.create(
            company=self.company,
            name=sku,
            sku=sku,
            supplier=self.supplier,
            unit=self.unit,
            is_stock_item=True,
            minimum_stock_level=Decimal(minimum),
            average_monthly_consumption=Decimal(monthly) if monthly is not None else None,
            consumption_calculation_mode=mode,
            purchase_batch_size=Decimal(batch) if batch is not None else None,
        )
        WarehouseStock.objects.create(
            company=self.company,
            product=product,
            quantity_on_hand=Decimal(on_hand),
            quantity_reserved=Decimal(reserved),
            quantity_expected=Decimal(expected),
        )
        return product

    def create_status_examples(self):
        self.create_stock('OUT', '0', '0', '200', '100', '0')
        self.create_stock('BELOW', '80', '0', '200', '100', '0')
        self.create_stock('ORDER', '150', '0', '0', '100', '100')
        self.create_stock('EXPECTED', '150', '0', '60', '100', '100')
        self.create_stock('NORMAL', '300', '0', '0', '100', '100')

    def test_calculation_assigns_all_statuses_and_recommendation(self):
        self.create_status_examples()

        rows = {row['sku']: row for row in stock_control_rows(self.company, self.settings)}

        self.assertEqual(rows['OUT']['status'], 'out_of_stock')
        self.assertEqual(rows['BELOW']['status'], 'below_minimum')
        self.assertEqual(rows['ORDER']['status'], 'requires_order')
        self.assertEqual(rows['ORDER']['projected_stock'], '50.00')
        self.assertEqual(rows['ORDER']['shortage_at_delivery'], '50.00')
        self.assertIsNone(rows['ORDER']['recommended_order_quantity'])
        self.assertEqual(rows['EXPECTED']['status'], 'supply_expected')
        self.assertEqual(rows['EXPECTED']['projected_stock'], '110.00')
        self.assertEqual(rows['NORMAL']['status'], 'normal')

    def test_reserved_quantity_reduces_available_and_forecast(self):
        self.create_stock('RESERVED', '200', '80', '0', '100', '30')

        row = stock_control_rows(self.company, self.settings)[0]

        self.assertEqual(row['quantity_available'], '120.00')
        self.assertEqual(row['consumption_during_lead'], '30.00')
        self.assertEqual(row['projected_stock'], '90.00')
        self.assertEqual(row['shortage_at_delivery'], '10.00')
        self.assertIsNone(row['recommended_order_quantity'])
        self.assertEqual(row['status'], 'requires_order')

    def test_recommendation_rounds_shortage_up_to_purchase_batch(self):
        self.create_stock('BATCHED', '60', '0', '0', '50', '20', '50')
        self.settings.stock_delivery_lead_days = 15

        row = stock_control_rows(self.company, self.settings)[0]

        self.assertEqual(row['projected_stock'], '50.00')
        self.assertEqual(row['shortage_at_delivery'], '0.00')
        self.assertEqual(row['recommended_order_quantity'], '0.00')

        stock = WarehouseStock.objects.get(product__sku='BATCHED')
        stock.quantity_on_hand = Decimal('57.80')
        stock.save(update_fields=['quantity_on_hand'])
        row = stock_control_rows(self.company, self.settings)[0]
        self.assertEqual(row['shortage_at_delivery'], '2.20')
        self.assertEqual(row['recommended_order_quantity'], '50.00')

    def test_missing_consumption_does_not_report_false_normal_forecast(self):
        self.create_stock('NO-FORECAST', '80', '0', '20', '50', None, '50')

        row = stock_control_rows(self.company, self.settings)[0]

        self.assertEqual(row['status'], 'normal')
        self.assertEqual(row['forecast_quality'], 'insufficient')
        self.assertEqual(row['forecast_quality_label'], 'No data')
        self.assertIsNone(row['projected_stock'])
        self.assertIsNone(row['shortage_at_delivery'])
        self.assertIsNone(row['recommended_order_quantity'])

    def test_automatic_consumption_uses_shipped_history_and_reports_confidence(self):
        product = self.create_stock(
            'AUTO', '100', '0', '0', '50', None, '50', mode='automatic',
        )
        Product.objects.filter(pk=product.pk).update(
            created_at=timezone.now() - timedelta(days=44),
        )
        for index in range(3):
            StockMovement.objects.create(
                company=self.company,
                product=product,
                movement_type=StockMovement.TYPE_CUSTOMER_SHIPPED,
                quantity=Decimal('10.00'),
                source_key=f'auto-history:{index}',
            )

        row = stock_control_rows(self.company, self.settings)[0]

        self.assertEqual(row['consumption_source'], 'automatic')
        self.assertEqual(row['consumption_confidence'], 'preliminary')
        self.assertEqual(row['consumption_observed_days'], 45)
        self.assertEqual(row['average_monthly_consumption'], '20.00')
        self.assertTrue(row['has_consumption_data'])

    def test_automatic_consumption_waits_for_thirty_days_of_history(self):
        self.create_stock(
            'NEW-AUTO', '100', '0', '0', '50', None, '50', mode='automatic',
        )

        row = stock_control_rows(self.company, self.settings)[0]

        self.assertEqual(row['status'], 'normal')
        self.assertEqual(row['consumption_source'], 'automatic')
        self.assertEqual(row['consumption_confidence'], 'insufficient')
        self.assertEqual(row['forecast_quality_label'], 'No data')
        self.assertIsNone(row['average_monthly_consumption'])

    def test_live_stock_control_and_export_do_not_require_manual_snapshot(self):
        self.create_stock('LIVE', '80', '0', '0', '100', '0', '50')
        self.client.force_authenticate(self.user)

        live = self.client.get('/api/warehouse-stock-control/live/')
        exported = self.client.get('/api/warehouse-stock-control/live/export/')

        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.data['source'], 'live')
        self.assertIsNone(live.data['id'])
        self.assertEqual(live.data['summary']['below_minimum_count'], 1)
        self.assertEqual(exported.status_code, 200)
        self.assertFalse(StockControlSnapshot.objects.filter(company=self.company).exists())

    def test_notification_feed_combines_urgent_and_weekly_stock_events(self):
        product = self.create_stock('NOTICE', '40', '0', '0', '50', '20', '50')
        sync_critical_stock_alert(WarehouseStock.objects.get(product=product))
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/notifications/')

        self.assertEqual(response.status_code, 200)
        kinds = {item['kind'] for item in response.data['results']}
        self.assertEqual(kinds, {'stock_alert', 'stock_weekly'})
        self.assertEqual(response.data['unread_count'], 2)

        alert_item = next(item for item in response.data['results'] if item['kind'] == 'stock_alert')
        read = self.client.post('/api/notifications/read/', {
            'kind': alert_item['kind'],
            'source_id': alert_item['source_id'],
        }, format='json')
        self.assertEqual(read.status_code, 200)
        self.assertEqual(self.client.get('/api/notifications/').data['unread_count'], 1)

        hidden = self.client.post('/api/notifications/hide/', {
            'kind': alert_item['kind'],
            'source_id': alert_item['source_id'],
        }, format='json')
        self.assertEqual(hidden.status_code, 200)
        remaining = self.client.get('/api/notifications/').data['results']
        self.assertNotIn(alert_item['key'], {item['key'] for item in remaining})

    def test_notification_feed_excludes_items_older_than_thirty_days(self):
        product = self.create_stock('OLD-NOTICE', '40', '0', '0', '50', '20', '50')
        sync_critical_stock_alert(WarehouseStock.objects.get(product=product))
        StockAlert.objects.filter(product=product).update(
            created_at=timezone.now() - timedelta(days=31),
        )
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/notifications/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('stock_alert', {item['kind'] for item in response.data['results']})

    def test_warehouse_list_can_filter_attention_statuses(self):
        self.create_status_examples()
        self.client.force_authenticate(self.user)

        attention = self.client.get('/api/warehouse-stocks/', {'stock_control': 'attention'})
        normal = self.client.get('/api/warehouse-stocks/', {'stock_control': 'normal'})

        self.assertEqual(attention.status_code, 200)
        self.assertEqual(normal.status_code, 200)
        attention_rows = paginated_results(attention)
        normal_rows = paginated_results(normal)
        self.assertEqual({row['stock_control']['status'] for row in attention_rows}, {
            'out_of_stock', 'below_minimum', 'requires_order', 'supply_expected',
        })
        self.assertEqual(len(normal_rows), 1)
        self.assertEqual(normal_rows[0]['stock_control']['status'], 'normal')

    def test_due_snapshot_is_created_once_for_the_week(self):
        self.create_stock('CRITICAL', '80', '0', '0', '100', '0')
        instant = datetime(2026, 10, 7, 12, 0, tzinfo=datetime_timezone.utc)

        first = ensure_due_stock_control_snapshot(self.company, self.user, instant)
        second = ensure_due_stock_control_snapshot(self.company, self.user, instant)

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.schedule_date.isoformat(), '2026-10-05')
        self.assertEqual(StockControlSnapshot.objects.filter(company=self.company).count(), 1)
        self.client.force_authenticate(self.user)
        latest = self.client.get('/api/warehouse-stock-control/latest/')
        self.assertTrue(latest.data['has_unread_attention'])

    def test_manual_generate_dismiss_and_export(self):
        self.create_status_examples()
        self.client.force_authenticate(self.user)
        # Seed the due weekly snapshot first, matching the application's normal load.
        self.client.get('/api/warehouse-stock-control/latest/')

        generated = self.client.post('/api/warehouse-stock-control/generate/')
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(generated.data['summary']['attention_count'], 4)
        snapshot_id = generated.data['id']

        latest = self.client.get('/api/warehouse-stock-control/latest/')
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.data['snapshot']['id'], snapshot_id)
        self.assertTrue(latest.data['has_unread_attention'])

        exported = self.client.get(f'/api/warehouse-stock-control/{snapshot_id}/export/')
        self.assertEqual(exported.status_code, 200)
        workbook = load_workbook(BytesIO(b''.join(exported.streaming_content)), data_only=False)
        sheet = workbook['Stock control']
        self.assertEqual(sheet['A1'].value, 'Warehouse stock control')
        self.assertEqual(sheet['A6'].value, 'Status')
        self.assertEqual(sheet['A7'].value, 'Out of stock')
        self.assertEqual(sheet['B7'].value, 'OUT')
        self.assertIn('Deficit at delivery', [cell.value for cell in sheet[6]])
        self.assertIn('Recommended order', [cell.value for cell in sheet[6]])

        dismissed = self.client.post(f'/api/warehouse-stock-control/{snapshot_id}/dismiss/')
        self.assertEqual(dismissed.status_code, 200)
        latest = self.client.get('/api/warehouse-stock-control/latest/')
        self.assertFalse(latest.data['has_unread_attention'])
        self.assertTrue(latest.data['snapshot']['is_dismissed'])

    def test_snapshot_export_is_company_scoped(self):
        self.create_stock('NORMAL', '300', '0', '0', '100', '100')
        self.client.force_authenticate(self.user)
        snapshot_id = self.client.post('/api/warehouse-stock-control/generate/').data['id']

        self.client.force_authenticate(self.other_user)
        response = self.client.get(f'/api/warehouse-stock-control/{snapshot_id}/export/')

        self.assertEqual(response.status_code, 404)
