from decimal import Decimal
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from products.models import Product
from supplier_orders.models import SupplierOrder, SupplierOrderItem, SupplierOrderStatus
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
