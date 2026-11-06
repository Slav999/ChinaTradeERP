from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from PIL import Image as PILImage

from .order_documents import _product_thumbnail, build_customer_order_pdf, build_supplier_order_pdf


def sample_order():
    buffer = BytesIO()
    PILImage.new('RGB', (480, 180), '#537da1').save(buffer, 'PNG')
    photo = Mock()
    photo.open.side_effect = lambda mode: BytesIO(buffer.getvalue())
    company = SimpleNamespace(name='Example company', logo=None, work_email='example@example.com',
                              phone='', address='', bank_details='Example bank', base_currency_code='KZT')
    items = []
    for index, image in enumerate([photo, None]):
        product = SimpleNamespace(image=image, sku=f'DCD16-{index + 1}', name='Fabric sample with a longer product name',
                                  unit=SimpleNamespace(name='m'), sale_price=Decimal('1250.00'))
        items.append(SimpleNamespace(product=product, quantity=Decimal('57.80'), unit='m', discount_pct=Decimal('0.05')))
    manager = Mock()
    manager.select_related.return_value.all.return_value = items
    return SimpleNamespace(company=company, order_number='27', supplier=SimpleNamespace(name='Example factory'),
                           customer=SimpleNamespace(name='Example customer'), shipping_address='Example warehouse',
                           supplier_comment='', customer_comment='', discount_pct=Decimal('0'), items=manager)


class OrderDocumentPhotoTests(SimpleTestCase):
    def test_both_documents_embed_product_photo(self):
        for builder in (build_supplier_order_pdf, build_customer_order_pdf):
            with self.subTest(builder=builder.__name__):
                pdf = builder(sample_order())
                self.assertTrue(pdf.startswith(b'%PDF'))
                self.assertIn(b'/Subtype /Image', pdf)

    def test_missing_or_corrupt_photo_does_not_block_documents(self):
        order = sample_order()
        product = order.items.select_related().all()[0].product
        for contents in (b'broken image', None):
            if contents is None:
                product.image.open.side_effect = FileNotFoundError('Missing photo')
            else:
                product.image.open.side_effect = lambda mode: BytesIO(contents)
            self.assertEqual(_product_thumbnail(product), '')
            for builder in (build_supplier_order_pdf, build_customer_order_pdf):
                self.assertTrue(builder(order).startswith(b'%PDF'))

    def test_thumbnail_is_small_square(self):
        image = _product_thumbnail(sample_order().items.select_related().all()[0].product)
        self.assertEqual((image.imageWidth, image.imageHeight), (240, 240))
        self.assertEqual(image.drawWidth, image.drawHeight)
