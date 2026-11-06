from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from products.models import CompanySettings, Product, ProductCategory, ProductChangeLog, Unit
from supplier_orders.models import SupplierOrder, SupplierOrderStatus
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
            cny_to_local_rate=Decimal('10.00'),
            usd_to_local_rate=Decimal('20.00'),
            logistics_cost_per_kg_usd=Decimal('3.00'),
        )

        self.client.force_authenticate(self.user_a)
        response = self.client.post('/api/settings/', {
            'cny_to_local_rate': '77.00',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            CompanySettings.objects.get(company=self.company_a).cny_to_local_rate,
            Decimal('77.00'),
        )
        self.assertEqual(
            CompanySettings.objects.get(company=self.company_b).cny_to_local_rate,
            Decimal('10.00'),
        )

    def test_admin_can_save_china_warehouse_address_in_company_settings(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post('/api/settings/', {
            'company_china_warehouse_address': '义乌市仓库地址',
        })

        self.assertEqual(response.status_code, 200)
        self.company_a.refresh_from_db()
        self.assertEqual(self.company_a.china_warehouse_address, '义乌市仓库地址')
        self.assertEqual(response.data['company_china_warehouse_address'], '义乌市仓库地址')

    def test_admin_can_save_company_language(self):
        self.client.force_authenticate(self.user_a)

        response = self.client.post('/api/settings/', {
            'company_language_code': 'en',
        })

        self.assertEqual(response.status_code, 200)
        self.company_a.refresh_from_db()
        self.assertEqual(self.company_a.language_code, 'en')
        self.assertEqual(response.data['company_language_code'], 'en')

    def test_non_admin_can_read_but_cannot_update_settings(self):
        self.client.force_authenticate(self.user_a_member)

        read_response = self.client.get('/api/settings/')
        write_response = self.client.post('/api/settings/', {
            'cny_to_local_rate': '88.00',
        })

        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(write_response.status_code, 403)

    def test_admin_can_save_stock_control_settings(self):
        self.client.force_authenticate(self.user_a)

        response = self.client.post('/api/settings/', {
            'stock_delivery_lead_days': 21,
            'stock_consumption_history_days': 180,
            'stock_timezone': 'Asia/Almaty',
            'stock_weekly_control_enabled': True,
            'stock_notification_weekday': 4,
            'stock_notification_time': '09:30',
        })

        self.assertEqual(response.status_code, 200)
        settings_obj = CompanySettings.objects.get(company=self.company_a)
        self.assertEqual(settings_obj.stock_delivery_lead_days, 21)
        self.assertEqual(settings_obj.stock_consumption_history_days, 180)
        self.assertEqual(settings_obj.stock_timezone, 'Asia/Almaty')
        self.assertEqual(settings_obj.stock_notification_weekday, 4)
        self.assertEqual(settings_obj.stock_notification_time.strftime('%H:%M'), '09:30')

    def test_invalid_stock_timezone_is_rejected(self):
        self.client.force_authenticate(self.user_a)

        response = self.client.post('/api/settings/', {
            'stock_timezone': 'Invalid/Zone',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('stock_timezone', response.data)

    @patch('products.currency.fetch_exchange_rate')
    def test_country_change_updates_currency_and_exchange_rates(self, fetch_exchange_rate):
        fetch_exchange_rate.side_effect = [
            Decimal('70.21'),
            Decimal('474.31'),
            Decimal('11.82'),
            Decimal('80.12'),
        ]
        CompanySettings.objects.create(
            company=self.company_a,
            cny_to_local_rate=Decimal('1.00'),
            usd_to_local_rate=Decimal('1.00'),
        )

        self.client.force_authenticate(self.user_a)
        response = self.client.post('/api/settings/', {
            'business_country': 'RU',
            'cny_to_local_rate': '1.00',
            'usd_to_local_rate': '1.00',
        })

        self.assertEqual(response.status_code, 200)
        self.company_a.refresh_from_db()
        settings_obj = CompanySettings.objects.get(company=self.company_a)
        self.assertEqual(str(self.company_a.business_country), 'RU')
        self.assertEqual(self.company_a.base_currency_code, 'RUB')
        self.assertEqual(settings_obj.cny_to_local_rate, Decimal('11.82'))
        self.assertEqual(settings_obj.usd_to_local_rate, Decimal('80.12'))
        self.assertIsNotNone(settings_obj.rates_updated_at)

    @patch('products.currency.fetch_exchange_rate')
    def test_country_change_fails_when_exchange_rates_are_unavailable(self, fetch_exchange_rate):
        fetch_exchange_rate.side_effect = [None, None]
        CompanySettings.objects.create(
            company=self.company_a,
            cny_to_local_rate=Decimal('70.21'),
            usd_to_local_rate=Decimal('474.31'),
        )
        self.company_a.apply_country_defaults('KZ')
        self.company_a.save()

        self.client.force_authenticate(self.user_a)
        response = self.client.post('/api/settings/', {
            'business_country': 'RU',
            'cny_to_local_rate': '70.21',
            'usd_to_local_rate': '474.31',
        })

        self.assertEqual(response.status_code, 400)
        self.company_a.refresh_from_db()
        settings_obj = CompanySettings.objects.get(company=self.company_a)
        self.assertEqual(str(self.company_a.business_country), 'KZ')
        self.assertEqual(self.company_a.base_currency_code, 'KZT')
        self.assertEqual(settings_obj.cny_to_local_rate, Decimal('70.21'))


class ProductSalePriceCalculationTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name='Calc Company')
        from users.access import ensure_default_access_structure
        roles = ensure_default_access_structure(self.company)
        self.user = User.objects.create_user(
            username='calc-user',
            access_role=roles['WED manager'],
            email='calc@example.com',
            password='password123',
            company=self.company,
            is_email_verified=True,
        )
        self.admin_user = User.objects.create_user(
            username='calc-admin',
            email='calc-admin@example.com',
            password='password123',
            company=self.company,
            is_company_admin=True,
            is_email_verified=True,
        )
        self.settings = CompanySettings.objects.create(
            company=self.company,
            cny_to_local_rate=Decimal('10.00'),
            usd_to_local_rate=Decimal('500.00'),
            logistics_cost_per_kg_usd=Decimal('2.00'),
            retail_tax_pct=Decimal('0.20'),
            acquiring_pct=Decimal('0.01'),
            packaging_pct=Decimal('0.01'),
            margin_pct=Decimal('0.50'),
        )
        self.supplier = Counterparty.objects.create(
            company=self.company,
            name='Supplier',
            type='china',
            is_supplier=True,
        )

    def test_sale_price_is_calculated_on_backend_without_discount(self):
        product = Product.objects.create(
            name='Calculator Product',
            sku='CALC-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
            units_per_package=10,
            weight_kg=Decimal('1.00'),
        )

        self.assertEqual(product.calculate_cost_price(self.settings), Decimal('1111.00'))
        self.assertEqual(product.calculate_sale_price(self.settings), Decimal('2109'))

    def test_sale_price_includes_internal_logistics(self):
        self.settings.internal_logistics_pct = Decimal('0.1000')
        product = Product.objects.create(
            name='Internal Logistics Product',
            sku='INTERNAL-LOGISTICS-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
            units_per_package=10,
            weight_kg=Decimal('1.00'),
        )

        self.assertEqual(product.calculate_cost_price(self.settings), Decimal('1222.10'))
        self.assertEqual(product.calculate_sale_price(self.settings), Decimal('2320'))

    def test_product_api_ignores_submitted_sale_price_and_uses_backend_formula(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.post('/api/products/', {
            'name': 'API Calculator Product',
            'sku': 'API-CALC-001',
            'supplier_id': self.supplier.id,
            'purchase_price': '10.00',
            'sale_price': '1.00',
            'units_per_package': 10,
            'weight_kg': '1.00',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['cost_price'], Decimal('1111.00'))
        self.assertEqual(response.data['sale_price'], '2109.00')

    def test_category_margin_update_recalculates_existing_products(self):
        category = ProductCategory.objects.create(company=self.company, name='Textile')
        self.client.force_authenticate(self.admin_user)
        create_response = self.client.post('/api/products/', {
            'name': 'Category Margin Product',
            'sku': 'CATEGORY-MARGIN-001',
            'category_id': category.id,
            'supplier_id': self.supplier.id,
            'purchase_price': '10.00',
            'units_per_package': 10,
            'weight_kg': '1.00',
        })
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data['sale_price'], '2109.00')

        self.client.force_authenticate(self.admin_user)
        update_response = self.client.patch(f'/api/product-category/{category.id}/', {
            'margin_pct': '0.3500',
        })

        self.assertEqual(update_response.status_code, 200)
        product = Product.objects.get(sku='CATEGORY-MARGIN-001')
        self.assertEqual(product.sale_price, Decimal('1899.00'))

    def test_sale_price_compensates_revenue_deductions_and_rounds_kzt(self):
        product = Product.objects.create(
            company=self.company,
            name='Rounded KZT Product',
            sku='ROUNDED-KZT-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
            weight_kg=Decimal('1.00'),
        )

        price = product.calculate_sale_price(self.settings)

        self.assertEqual(price, Decimal('2109'))
        net_after_deductions = price * (
            Decimal('1.00') - self.settings.retail_tax_pct - self.settings.acquiring_pct
        )
        target = product.calculate_cost_price(self.settings) * (Decimal('1.00') + self.settings.margin_pct)
        self.assertLess(abs(net_after_deductions - target), Decimal('0.50'))

    def test_non_kzt_and_non_rub_prices_keep_two_decimal_places(self):
        self.company.base_currency_code = 'USD'
        self.company.save(update_fields=['base_currency_code'])
        product = Product.objects.create(
            company=self.company,
            name='USD Product',
            sku='USD-PRICE-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
            weight_kg=Decimal('1.00'),
        )

        self.assertEqual(product.calculate_sale_price(self.settings), Decimal('2109.49'))

    def test_product_api_keeps_automatic_prices_zero_when_weight_is_missing(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.post('/api/products/', {
            'name': 'No Weight Product',
            'sku': 'NO-WEIGHT-001',
            'supplier_id': self.supplier.id,
            'purchase_price': '10.00',
            'units_per_package': 10,
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['cost_price'], Decimal('0.00'))
        self.assertEqual(response.data['sale_price'], '0.00')

    def test_admin_can_set_manual_sale_price_and_settings_changes_preserve_it(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.post('/api/products/', {
            'name': 'Manual Price Product',
            'sku': 'MANUAL-PRICE-001',
            'supplier_id': self.supplier.id,
            'purchase_price': '10.00',
            'sale_price_mode': 'manual',
            'sale_price': '777.00',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['sale_price'], '777.00')
        self.settings.cny_to_local_rate = Decimal('12.00')
        self.settings.save()
        product = Product.objects.get(sku='MANUAL-PRICE-001')
        self.assertEqual(product.sale_price, Decimal('777.00'))

    def test_regular_user_cannot_set_manual_sale_price(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/products/', {
            'name': 'Forbidden Manual Price',
            'sku': 'FORBIDDEN-MANUAL-001',
            'supplier_id': self.supplier.id,
            'purchase_price': '10.00',
            'sale_price_mode': 'manual',
            'sale_price': '1.00',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('sale_price', response.data)

    def test_delete_unused_product_removes_it_permanently(self):
        product = Product.objects.create(
            company=self.company,
            name='Unused Product',
            sku='UNUSED-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
        )
        self.client.force_authenticate(self.user)

        response = self.client.delete(f'/api/products/{product.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(id=product.id).exists())

    def test_unused_product_can_be_archived_without_deleting_it(self):
        product = Product.objects.create(
            company=self.company,
            name='Seasonal Product',
            sku='SEASONAL-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(f'/api/products/{product.id}/archive/')

        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertTrue(product.is_archived)
        self.assertTrue(
            ProductChangeLog.objects.filter(
                product=product,
                field_name='is_archived',
                old_value='False',
                new_value='True',
                changed_by=self.user,
            ).exists()
        )

    def test_delete_used_product_archives_it(self):
        product = Product.objects.create(
            company=self.company,
            name='Used Product',
            sku='USED-001',
            supplier=self.supplier,
            purchase_price=Decimal('10.00'),
        )
        customer = Counterparty.objects.create(
            company=self.company,
            name='Customer',
            type='local',
            is_customer=True,
        )
        status = CustomerOrderStatus.objects.create(company=self.company, name='New')
        order = CustomerOrder.objects.create(
            company=self.company,
            order_number='1',
            status=status,
            customer=customer,
        )
        CustomerOrderItem.objects.create(order=order, product=product, quantity=Decimal('1.00'))
        self.client.force_authenticate(self.user)

        response = self.client.delete(f'/api/products/{product.id}/')

        self.assertEqual(response.status_code, 204)
        product.refresh_from_db()
        self.assertTrue(product.is_archived)
        self.assertIsNotNone(product.archived_at)
        self.assertTrue(
            ProductChangeLog.objects.filter(
                product=product,
                field_name='is_archived',
                old_value='False',
                new_value='True',
                changed_by=self.user,
            ).exists()
        )

    def test_archived_filter_and_restore_product(self):
        product = Product.objects.create(
            company=self.company,
            name='Archived Product',
            sku='ARCHIVED-001',
            supplier=self.supplier,
            is_archived=True,
        )
        self.client.force_authenticate(self.user)

        active_response = self.client.get('/api/products/', {'archive_status': 'active'})
        archived_response = self.client.get('/api/products/', {'archive_status': 'archived'})
        restore_response = self.client.post(f'/api/products/{product.id}/restore/')

        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(archived_response.status_code, 200)
        self.assertEqual(restore_response.status_code, 200)
        self.assertNotIn(product.id, [item['id'] for item in active_response.data['results']])
        self.assertIn(product.id, [item['id'] for item in archived_response.data['results']])
        product.refresh_from_db()
        self.assertFalse(product.is_archived)
        self.assertTrue(
            ProductChangeLog.objects.filter(
                product=product,
                field_name='is_archived',
                old_value='True',
                new_value='False',
                changed_by=self.user,
            ).exists()
        )

    def test_non_admin_cannot_permanently_delete_product(self):
        product = Product.objects.create(
            company=self.company,
            name='Archived Product',
            sku='ARCHIVED-DELETE-001',
            supplier=self.supplier,
            is_archived=True,
        )
        self.client.force_authenticate(self.user)

        response = self.client.delete(f'/api/products/{product.id}/permanent-delete/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(id=product.id).exists())

    def test_archived_product_cannot_be_added_to_customer_order_item(self):
        product = Product.objects.create(
            company=self.company,
            name='Archived Customer Product',
            sku='ARCHIVED-CUSTOMER-001',
            supplier=self.supplier,
            is_archived=True,
        )
        customer = Counterparty.objects.create(
            company=self.company,
            name='Customer',
            type='local',
            is_customer=True,
        )
        status = CustomerOrderStatus.objects.create(company=self.company, name='New')
        order = CustomerOrder.objects.create(
            company=self.company,
            order_number='2',
            status=status,
            customer=customer,
        )
        self.client.force_authenticate(self.admin_user)

        response = self.client.post('/api/customer-order-items/', {
            'order': order.id,
            'product_id': product.id,
            'quantity': '1.00',
        })

        self.assertEqual(response.status_code, 400)

    def test_archived_product_cannot_be_added_to_supplier_order_item(self):
        product = Product.objects.create(
            company=self.company,
            name='Archived Supplier Product',
            sku='ARCHIVED-SUPPLIER-001',
            supplier=self.supplier,
            is_archived=True,
        )
        status = SupplierOrderStatus.objects.create(company=self.company, name='New')
        order = SupplierOrder.objects.create(
            company=self.company,
            order_number='2',
            status=status,
            supplier=self.supplier,
        )
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/supplier-order-items/', {
            'order': order.id,
            'product_id': product.id,
            'quantity': '1.00',
        })

        self.assertEqual(response.status_code, 400)

    def test_non_admin_cannot_delete_product_category(self):
        category = ProductCategory.objects.create(company=self.company, name='Textile')
        self.client.force_authenticate(self.user)

        response = self.client.delete(f'/api/product-category/{category.id}/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ProductCategory.objects.filter(id=category.id).exists())

    def test_admin_cannot_delete_unit_used_by_product(self):
        unit = Unit.objects.create(company=self.company, name='m')
        Product.objects.create(
            name='Used Unit Product',
            sku='USED-UNIT-001',
            supplier=self.supplier,
            unit=unit,
            purchase_price=Decimal('10.00'),
            units_per_package=10,
            weight_kg=Decimal('1.00'),
        )
        self.client.force_authenticate(self.admin_user)

        response = self.client.delete(f'/api/units/{unit.id}/')

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Unit.objects.filter(id=unit.id).exists())

    def test_admin_can_delete_unit_used_only_by_archived_product(self):
        unit = Unit.objects.create(company=self.company, name='kg')
        Product.objects.create(
            name='Archived Unit Product',
            sku='ARCHIVED-UNIT-001',
            supplier=self.supplier,
            unit=unit,
            purchase_price=Decimal('10.00'),
            units_per_package=10,
            weight_kg=Decimal('1.00'),
            is_archived=True,
        )
        self.client.force_authenticate(self.admin_user)

        response = self.client.delete(f'/api/units/{unit.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Unit.objects.filter(id=unit.id).exists())
