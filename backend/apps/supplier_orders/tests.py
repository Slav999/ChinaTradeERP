from decimal import Decimal
from datetime import UTC, datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from products.models import Product
from supplier_orders.models import SupplierOrder, SupplierOrderChangeLog, SupplierOrderItem, SupplierOrderStatus
from supplier_orders.models import ShippingAddress as SupplierShippingAddress
from supplier_orders.serializers import SupplierOrderChangeLogSerializer
from users.models import Company, CustomUser


class SupplierOrderRepresentationTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)

    def setUp(self):
        self.company = Company.objects.create(name='Acme')
        self.user = CustomUser.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='pass',
            company=self.company,
            is_company_admin=True,
        )
        self.client.force_authenticate(self.user)
        self.status = SupplierOrderStatus.objects.create(
            company=self.company,
            name='Received',
            color='#28a745',
        )
        self.supplier = Counterparty.objects.create(
            company=self.company,
            name='Supplier',
            type='china',
            is_supplier=True,
            qr_code_image=SimpleUploadedFile(
                'supplier-qr.png',
                b'fake-image-content',
                content_type='image/png',
            ),
        )
        self.product = Product.objects.create(
            company=self.company,
            name='Fabric',
            sku='FAB-001',
            supplier=self.supplier,
            purchase_price=Decimal('12.50'),
            sale_price=Decimal('25.00'),
        )
        self.order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.status,
            amount_cny=None,
            payment_details_qr=SimpleUploadedFile(
                'old-order-qr.png',
                b'old-image-content',
                content_type='image/png',
            ),
            created_by=self.user,
            updated_by=self.user,
        )
        SupplierOrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=Decimal('4.00'),
            unit_price_cny=Decimal('12.50'),
        )

    def test_detail_falls_back_to_line_total_and_supplier_qr(self):
        response = self.client.get(f'/api/supplier-order/{self.order.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount_cny'], '50.00')
        self.assertIn('supplier-qr', response.data['payment_details_qr'])
        self.assertNotIn('old-order-qr', response.data['payment_details_qr'])

    def test_list_falls_back_to_line_total_and_supplier_qr(self):
        response = self.client.get('/api/supplier-order/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first = response.data['results'][0]
        self.assertEqual(first['amount_cny'], '50.00')
        self.assertIn('supplier-qr', first['payment_details_qr'])
        self.assertNotIn('old-order-qr', first['payment_details_qr'])

    def test_shipping_address_can_be_cleared_on_existing_order(self):
        self.company.china_warehouse_address = 'Moscow warehouse'
        self.company.save(update_fields=['china_warehouse_address'])
        self.order.shipping_address = 'Old address'
        self.order.save(update_fields=['shipping_address'])

        response = self.client.patch(
            f'/api/supplier-order/{self.order.id}/',
            {'shipping_address': ''},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.shipping_address, '')

    def test_new_supplier_order_uses_company_china_warehouse_address(self):
        self.company.china_warehouse_address = 'Moscow warehouse'
        self.company.save(update_fields=['china_warehouse_address'])
        SupplierShippingAddress.objects.create(
            company=self.company,
            default_shipping_address='Legacy Moscow warehouse',
        )

        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.status,
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(order.shipping_address, 'Moscow warehouse')

    def test_new_supplier_order_ignores_legacy_shipping_address_when_company_address_is_empty(self):
        SupplierShippingAddress.objects.create(
            company=self.company,
            default_shipping_address='Legacy Moscow warehouse',
        )

        order = SupplierOrder.objects.create(
            company=self.company,
            supplier=self.supplier,
            status=self.status,
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(order.shipping_address, '')

    def test_change_history_uses_project_local_time(self):
        log = SupplierOrderChangeLog.objects.create(
            supplier_order=self.order,
            field_name='shipping_address',
            old_value='Old',
            new_value='',
            changed_by=self.user,
        )
        log.changed_at = datetime(2026, 8, 26, 10, 6, tzinfo=UTC)
        log.save(update_fields=['changed_at'])

        data = SupplierOrderChangeLogSerializer(log).data

        self.assertEqual(data['changed_at'], '2026-08-26 15:06')

    def test_item_purchase_price_is_snapshotted_and_not_changed_with_product(self):
        item = self.order.items.get()
        self.assertEqual(item.unit_price_cny, Decimal('12.50'))

        self.product.purchase_price = Decimal('99.00')
        self.product.save(update_fields=['purchase_price'])
        item.refresh_from_db()

        self.assertEqual(item.unit_price_cny, Decimal('12.50'))

    def test_item_purchase_price_can_be_changed_and_is_logged(self):
        item = self.order.items.get()

        response = self.client.patch(
            f'/api/supplier-order-items/{item.id}/',
            {'unit_price_cny': '11.75'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.unit_price_cny, Decimal('11.75'))
        log = SupplierOrderChangeLog.objects.get(
            supplier_order=self.order,
            field_name='item_unit_price_cny',
        )
        self.assertEqual(log.old_value, 'FAB-001: 12.50')
        self.assertEqual(log.new_value, 'FAB-001: 11.75')
        self.assertEqual(log.changed_by, self.user)

    def test_item_purchase_price_cannot_be_negative(self):
        item = self.order.items.get()

        response = self.client.patch(
            f'/api/supplier-order-items/{item.id}/',
            {'unit_price_cny': '-0.01'},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('unit_price_cny', response.data)
        item.refresh_from_db()
        self.assertEqual(item.unit_price_cny, Decimal('12.50'))
