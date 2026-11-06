from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook
from rest_framework.test import APITestCase

from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from products.models import Product
from supplier_orders.models import SupplierOrder, SupplierOrderItem, SupplierOrderStatus
from users.models import Company, CustomUser


class OrderReportTests(APITestCase):
    def analytics(self, kind, params):
        response = self.client.get(f'/api/{kind}-order/analytics/', params)
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(b''.join(response.streaming_content)), data_only=True)
        self.assertEqual(workbook.sheetnames, ['Analytics'])
        self.assertIsNone(workbook.active.sheet_view.pane)
        self.assertEqual(len(workbook.active.sheet_view.selection), 1)
        self.assertIsNone(workbook.active.sheet_view.selection[0].pane)
        self.assertEqual(workbook.active.sheet_view.selection[0].sqref, 'A1')
        self.assertIsNone(workbook.active.auto_filter.ref)
        self.assertTrue(all(
            cell.alignment.horizontal == 'left'
            for row in workbook.active.iter_rows()
            for cell in row
            if cell.value is not None
        ))
        text_values = {
            value
            for row in workbook.active.iter_rows(values_only=True)
            for value in row
            if isinstance(value, str)
        }
        self.assertFalse(any('order-level amount overrides' in value for value in text_values))
        expected_title_range = 'A1:L1' if kind == 'supplier' else 'A1:J1'
        self.assertIn(expected_title_range, {str(item) for item in workbook.active.merged_cells.ranges})
        self.assertEqual(len(workbook.active._charts), 1)
        chart = workbook.active._charts[0]
        self.assertTrue(chart.dLbls.showVal)
        self.assertFalse(chart.dLbls.showSerName)
        self.assertFalse(chart.dLbls.showCatName)
        self.assertEqual(chart.dLbls.dLblPos, 'outEnd')
        self.assertEqual(chart.x_axis.scaling.orientation, 'maxMin')
        self.assertFalse(any(cell.value == 'Notes' for row in workbook.active.iter_rows() for cell in row))
        summary_last_row = max(
            cell.row
            for row in workbook.active.iter_rows()
            for cell in row
            if (
                isinstance(cell.value, str)
                and cell.value.startswith('Total,')
                and cell.row < chart.anchor._from.row + 1
            )
        )
        self.assertGreaterEqual(chart.anchor._from.row + 1, summary_last_row + 3)
        self.assertGreaterEqual(workbook.active.row_dimensions[summary_last_row].height, 34)
        ranking_header_row = next(
            row[0].row
            for row in workbook.active.iter_rows()
            if row[0].value == 'Rank' and row[1].value == kind.title()
        )
        self.assertEqual(ranking_header_row, chart.anchor.to.row + 3)
        for row_number in range(chart.anchor.to.row + 1, ranking_header_row):
            self.assertTrue(all(cell.value is None for cell in workbook.active[row_number]))
            self.assertGreaterEqual(workbook.active.row_dimensions[row_number].height, 20)
        products_title = f'Top 5 products per {kind}'
        products_title_row = next(
            cell.row for row in workbook.active.iter_rows() for cell in row if cell.value == products_title
        )
        for spacer_row in range(products_title_row - 2, products_title_row):
            self.assertTrue(all(cell.value is None for cell in workbook.active[spacer_row]))
            self.assertGreaterEqual(workbook.active.row_dimensions[spacer_row].height, 20)
        self.assertFalse(any(
            isinstance(value, str) and value.startswith('Shows up to five products')
            for row in workbook.active.iter_rows(values_only=True)
            for value in row
        ))
        return list(workbook.active.values)

    def test_supplier_analytics_scope_period_and_defects(self):
        from django.utils import timezone
        from datetime import timedelta
        for quantity, defective in ((2, Decimal('0.5')), (3, Decimal('1.0'))):
            order = SupplierOrder.objects.create(company=self.company, supplier=self.supplier, status=self.ss)
            SupplierOrderItem.objects.create(
                order=order, product=self.product, quantity=quantity,
                defective_quantity=defective, unit='m',
            )
        cancelled = SupplierOrderStatus.objects.create(company=self.company, name='Cancelled')
        SupplierOrder.objects.create(company=self.company, supplier=self.supplier, status=cancelled, amount_cny=999)
        old = SupplierOrder.objects.create(company=self.company, supplier=self.supplier, status=self.ss, amount_cny=888)
        SupplierOrder.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=60))
        other = Company.objects.create(name='Other')
        SupplierOrder.objects.create(company=other, supplier=self.supplier, status=self.ss, amount_cny=777)
        rows = self.analytics('supplier', {'date_from': str(timezone.localdate() - timedelta(days=7)),
                                           'counterparty': self.supplier.pk, 'search': 'missing', 'status': cancelled.pk,
                                           'customer_query': 'missing'})
        rank = next(row for row in rows if row[0] == 1)
        self.assertEqual(rank[1:3], ('BD', 2))
        self.assertEqual(rank[4], 50)
        self.assertEqual(rank[8:10], ('1.50 m', '30.00% m'))
        top = next(row for row in rows if row[0] == 1 and row[1] == 'BD' and row[2] == 'TEST')
        self.assertEqual(top[4:9], (2, 5, 'm', 1.5, 30))
        self.assertEqual(self.client.get('/api/supplier-order/analytics/', {'date_from': '2026-10-01', 'date_to': '2026-01-01'}).status_code, 400)
        outsider = Counterparty.objects.create(company=other, name='Foreign', type='china', is_supplier=True)
        self.assertEqual(self.client.get('/api/supplier-order/analytics/', {'counterparty': outsider.pk}).status_code, 400)

    def test_supplier_ranking_uses_total_cny(self):
        frequent = Counterparty.objects.create(
            company=self.company, name='Frequent low value', type='china', is_supplier=True,
        )
        high_value = Counterparty.objects.create(
            company=self.company, name='High value', type='china', is_supplier=True,
        )
        for _ in range(3):
            order = SupplierOrder.objects.create(company=self.company, supplier=frequent, status=self.ss)
            SupplierOrderItem.objects.create(order=order, product=self.product, quantity=1, unit='m')
        order = SupplierOrder.objects.create(company=self.company, supplier=high_value, status=self.ss)
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=10, unit='m')
        rows = self.analytics('supplier', {})
        ranking_rows = [row for row in rows if isinstance(row[0], int) and isinstance(row[2], int)]
        self.assertEqual(ranking_rows[0][1], 'High value')
        self.assertEqual(ranking_rows[1][1], 'Frequent low value')

    def test_supplier_ranking_uses_name_only_when_cny_totals_match(self):
        alphabetical = Counterparty.objects.create(
            company=self.company, name='Alpha supplier', type='china', is_supplier=True,
        )
        frequent = Counterparty.objects.create(
            company=self.company, name='Zulu supplier', type='china', is_supplier=True,
        )
        order = SupplierOrder.objects.create(company=self.company, supplier=alphabetical, status=self.ss)
        SupplierOrderItem.objects.create(order=order, product=self.product, quantity=3, unit='m')
        for _ in range(3):
            order = SupplierOrder.objects.create(company=self.company, supplier=frequent, status=self.ss)
            SupplierOrderItem.objects.create(order=order, product=self.product, quantity=1, unit='m')
        rows = self.analytics('supplier', {})
        ranking_rows = [row for row in rows if isinstance(row[0], int) and isinstance(row[2], int)]
        self.assertEqual([row[1] for row in ranking_rows[:2]], ['Alpha supplier', 'Zulu supplier'])

    def test_customer_analytics_ranking_discounts_and_top_five(self):
        buyer = Counterparty.objects.create(company=self.company, name='Large buyer', type='local', is_customer=True)
        order = CustomerOrder.objects.create(company=self.company, customer=buyer, status=self.cs, discount_pct=Decimal('0.1'))
        for index in range(7):
            product = Product.objects.create(company=self.company, supplier=self.supplier, name=f'Product {index}', sku=f'P{index}', sale_price=10)
            CustomerOrderItem.objects.create(order=order, product=product, quantity=index + 1, unit='m')
        small = CustomerOrder.objects.create(company=self.company, customer=self.customer, status=self.cs)
        CustomerOrderItem.objects.create(order=small, product=self.product, quantity=1, unit='pcs')
        rows = self.analytics('customer', {'search': 'missing', 'supplier_query': 'missing'})
        rank = next(row for row in rows if row[0] == 1)
        self.assertEqual(rank[1], 'Large buyer')
        self.assertEqual(rank[4], 252)
        self.assertEqual(rank[7], 252)
        products = [row for row in rows if row[1] == 'Large buyer' and isinstance(row[0], int) and isinstance(row[2], str)]
        self.assertEqual(len(products), 5)
        self.assertEqual(products[0][2], 'P6')
        self.assertEqual(products[0][4], 'BD')
        selected = self.analytics('customer', {'counterparty': self.customer.pk})
        self.assertEqual(len([row for row in selected if isinstance(row[0], int) and isinstance(row[2], int)]), 1)

    def test_analytics_ranking_limits(self):
        for index in range(35):
            supplier = Counterparty.objects.create(
                company=self.company, name=f'Supplier {index:02}', type='china', is_supplier=True,
            )
            order = SupplierOrder.objects.create(company=self.company, supplier=supplier, status=self.ss)
            SupplierOrderItem.objects.create(order=order, product=self.product, quantity=index + 1)
        top_ten = self.analytics('supplier', {'ranking_limit': '10'})
        self.assertEqual(len([row for row in top_ten if isinstance(row[0], int) and isinstance(row[2], int)]), 10)
        all_suppliers = self.analytics('supplier', {'ranking_limit': 'all'})
        self.assertEqual(len([row for row in all_suppliers if isinstance(row[0], int) and isinstance(row[2], int)]), 35)
        self.assertEqual(self.client.get('/api/supplier-order/analytics/', {'ranking_limit': '20'}).status_code, 400)
        self.assertEqual(self.client.get('/api/customer-order/analytics/', {'ranking_limit': '31'}).status_code, 400)

    def setUp(self):
        self.company = Company.objects.create(name='Report company', language_code='en')
        self.user = CustomUser.objects.create_user(
            username='report',
            password='pass',
            company=self.company,
            is_company_admin=True,
        )
        self.client.force_authenticate(self.user)
        self.supplier = Counterparty.objects.create(company=self.company, name='BD', type='china', is_supplier=True)
        self.customer = Counterparty.objects.create(company=self.company, name='Buyer', type='local', is_customer=True)
        self.product = Product.objects.create(company=self.company, supplier=self.supplier, name='=literal product',
                                              sku='TEST', purchase_price=Decimal('10'), sale_price=Decimal('25'))
        self.ss = SupplierOrderStatus.objects.create(company=self.company, name='New')
        self.cs = CustomerOrderStatus.objects.create(company=self.company, name='New')

    def export(self, kind, params):
        response = self.client.get(f'/api/{kind}-order/export/', params)
        self.assertEqual(response.status_code, 200)
        return load_workbook(BytesIO(b''.join(response.streaming_content)), data_only=False)

    def rows(self, sheet):
        header = next(row[0].row for row in sheet if row[0].value == 'Order #')
        names = [cell.value for cell in sheet[header]]
        totals_row = next(row[0].row for row in sheet if row[0].value == 'Totals')
        end = totals_row - 2
        return [dict(zip(names, values)) for values in sheet.iter_rows(min_row=header + 1, max_row=end, values_only=True)] if end > header else []

    def test_export_uses_company_language(self):
        self.company.language_code = 'ru'
        self.company.save(update_fields=['language_code'])
        SupplierOrder.objects.create(company=self.company, supplier=self.supplier, status=self.ss)

        workbook = self.export('supplier', {})

        self.assertEqual(workbook.sheetnames, ['Заказы'])
        values = {
            cell.value
            for row in workbook.active.iter_rows()
            for cell in row
            if isinstance(cell.value, str)
        }
        self.assertIn('Отчёт по заказам поставщикам', values)
        self.assertIn('Заказ №', values)
        self.assertIn('Поставщик', values)
        self.assertIsNone(workbook.active.auto_filter.ref)
        self.assertIsNone(workbook.active.freeze_panes)

    def test_russian_analytics_charts_reference_localized_sheet(self):
        self.company.language_code = 'ru'
        self.company.save(update_fields=['language_code'])
        supplier_order = SupplierOrder.objects.create(company=self.company, supplier=self.supplier, status=self.ss)
        SupplierOrderItem.objects.create(order=supplier_order, product=self.product, quantity=2, unit='m')
        customer_order = CustomerOrder.objects.create(company=self.company, customer=self.customer, status=self.cs)
        CustomerOrderItem.objects.create(order=customer_order, product=self.product, quantity=2, unit='m')

        for kind in ('supplier', 'customer'):
            with self.subTest(kind=kind):
                response = self.client.get(f'/api/{kind}-order/analytics/')
                self.assertEqual(response.status_code, 200)
                workbook = load_workbook(BytesIO(b''.join(response.streaming_content)), data_only=False)

                self.assertEqual(workbook.sheetnames, ['Аналитика'])
                self.assertEqual(len(workbook.active._charts), 1)
                chart = workbook.active._charts[0]
                self.assertIn("'Аналитика'!", chart.series[0].val.numRef.f)
                self.assertIsNone(workbook.active.auto_filter.ref)
                self.assertIsNone(workbook.active.freeze_panes)

    def test_supplier_filters_details_defects_and_company_scope(self):
        order = SupplierOrder.objects.create(company=self.company, supplier=self.supplier, customer=self.customer,
                                             status=self.ss, shipping_code='match', track_number='TRACK-001')
        SupplierOrderItem.objects.create(
            order=order, product=self.product, quantity=3,
            defective_quantity=Decimal('0.75'), unit='m',
        )
        other_supplier = Counterparty.objects.create(company=self.company, name='Other', type='china', is_supplier=True)
        SupplierOrder.objects.create(company=self.company, supplier=other_supplier, status=self.ss)
        other_company = Company.objects.create(name='Other company')
        SupplierOrder.objects.create(company=other_company, supplier=self.supplier, status=self.ss)
        params = {'supplier_query': 'BD', 'customer_query': 'Buyer', 'status': self.ss.id, 'search': 'match', 'page_size': 1}
        workbook = self.export('supplier', params)
        rows = self.rows(workbook['Orders'])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Order #'], order.order_number)
        self.assertEqual(rows[0]['Defective quantity'], 0.75)
        self.assertEqual(rows[0]['Defect rate, %'], 25)
        self.assertEqual(rows[0]['Total, CNY'], 30)
        self.assertEqual(rows[0]['Track number'], 'TRACK-001')
        self.assertIn('Created at', rows[0])
        metadata = {
            row[0]: row[1]
            for row in workbook['Orders'].iter_rows(values_only=True)
            if row[0] in {'Active filters', 'Exported'}
        }
        self.assertIn('Supplier: BD', metadata['Active filters'])
        self.assertIn('Customer: Buyer', metadata['Active filters'])
        self.assertIn('Status: New', metadata['Active filters'])
        self.assertNotIn('Status ID', metadata['Active filters'])
        self.assertEqual(metadata['Exported'], '1 orders; 1 positions; all matching pages')
        item = self.rows(workbook['Orders'])[0]
        self.assertEqual(item['Quantity'], 3)
        self.assertEqual(item['Total, CNY'], 30)
        self.assertEqual(item['Product'], '=literal product')
        literal = next(c for row in workbook['Orders'] for c in row if c.value == '=literal product')
        self.assertEqual(literal.data_type, 's')
        for key, value in [('supplier_query', 'missing'), ('customer_query', 'missing'), ('status', 99999), ('search', 'missing')]:
            with self.subTest(key=key):
                self.assertEqual(self.rows(self.export('supplier', {**params, key: value})['Orders']), [])

    def test_customer_filters_discounts_and_all_pages(self):
        orders = []
        for _ in range(2):
            order = CustomerOrder.objects.create(company=self.company, customer=self.customer, status=self.cs,
                                                 discount_pct=Decimal('0.1'), shipping_code='match')
            CustomerOrderItem.objects.create(order=order, product=self.product, quantity=2)
            orders.append(order)
        other_company = Company.objects.create(name='Other company')
        CustomerOrder.objects.create(company=other_company, customer=self.customer, status=self.cs)
        params = {'customer_query': 'Buyer', 'status': self.cs.id, 'search': 'match', 'page_size': 1}
        workbook = self.export('customer', params)
        rows = self.rows(workbook['Orders'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['Total, local'], 45)
        self.assertEqual(rows[0]['Order discount, %'], 10)
        self.assertEqual(rows[0]['Product supplier'], 'BD')
        self.assertNotIn('Supplier', rows[0])
        self.assertNotIn('Has defects', rows[0])
        text_values = {
            value
            for row in workbook['Orders'].iter_rows(values_only=True)
            for value in row
            if isinstance(value, str)
        }
        self.assertFalse(any('Current sale prices' in value for value in text_values))
        self.assertIn('Totals', text_values)
        self.assertEqual(len(self.rows(workbook['Orders'])), 2)
        for key in ('customer_query', 'search', 'status'):
            with self.subTest(key=key):
                self.assertEqual(self.rows(self.export('customer', {**params, key: '99999'})['Orders']), [])

    def test_defective_quantity_can_be_saved_and_is_validated(self):
        order = SupplierOrder.objects.create(company=self.company, supplier=self.supplier, status=self.ss)
        item = SupplierOrderItem.objects.create(order=order, product=self.product, quantity=10)
        response = self.client.patch(
            f'/api/supplier-order-items/{item.id}/',
            {'defective_quantity': '2.00'}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['defective_quantity'], '2.00')
        for invalid in ('-1', '11'):
            with self.subTest(invalid=invalid):
                response = self.client.patch(
                    f'/api/supplier-order-items/{item.id}/',
                    {'defective_quantity': invalid}, format='json',
                )
                self.assertEqual(response.status_code, 400)

    def test_sku_search_exports_only_matching_lines_and_totals_on_one_sheet(self):
        self.product.sku = '12345-A'
        self.product.save()
        unrelated = Product.objects.create(company=self.company, supplier=self.supplier,
                                           name='Other', sku='OTHER', purchase_price=Decimal('100'))
        for quantity in (2, 3):
            order = SupplierOrder.objects.create(company=self.company, supplier=self.supplier, status=self.ss)
            order.cny_to_local_rate = Decimal('2')
            order.save(update_fields=['cny_to_local_rate'])
            SupplierOrderItem.objects.create(order=order, product=self.product, quantity=quantity, unit='m')
            SupplierOrderItem.objects.create(order=order, product=self.product, quantity=1, unit='m')
            SupplierOrderItem.objects.create(order=order, product=unrelated, quantity=99, unit='pcs')
        response = self.client.get('/api/supplier-order/', {'search': '123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        workbook = self.export('supplier', {'search': '123'})
        self.assertEqual(workbook.sheetnames, ['Orders'])
        sheet = workbook['Orders']
        rows = self.rows(sheet)
        self.assertEqual(len(rows), 4)
        self.assertEqual({row['SKU'] for row in rows}, {'12345-A'})
        self.assertEqual(sum(row['Quantity'] for row in rows), 7)
        self.assertEqual(sum(row['Total, CNY'] for row in rows), 70)
        self.assertEqual(sum(row['Total, local'] for row in rows), 140)
        values = {row[0]: row[1] for row in sheet.iter_rows(values_only=True) if row[0]}
        self.assertEqual(values['Orders count'], 2)
        self.assertEqual(values['Positions count'], 4)
        self.assertEqual(values['Total quantity, m'], 7)
        self.assertEqual(values['Total, CNY'], 70)
        header = next(row[0].row for row in sheet if row[0].value == 'Order #')
        first_group_fills = {rows[index]['Order #']: sheet.cell(header + 1 + index, 1).fill.fgColor.rgb for index in range(4)}
        self.assertEqual(len(set(first_group_fills.values())), 2)
