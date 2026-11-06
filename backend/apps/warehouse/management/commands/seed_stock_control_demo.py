from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from counterparties.models import Counterparty
from products.models import Product, Unit
from users.models import Company
from warehouse.models import StockMovement, WarehouseStock
from warehouse.services import sync_critical_stock_alert
from warehouse.stock_control import company_stock_settings, stock_control_item


DEMO_PREFIX = 'DEMO-STOCK-'
DEMO_MARKER = '[stock-control-demo]'


class Command(BaseCommand):
    help = 'Create repeatable warehouse-control demo data for a local company.'

    def add_arguments(self, parser):
        parser.add_argument('--company', required=True, help='Exact company name.')
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing DEMO-STOCK-* products before recreating the scenario.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete DEMO-STOCK-* products and stop without recreating them.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('This demo command is disabled when DEBUG=False.')

        try:
            company = Company.objects.get(name=options['company'])
        except Company.DoesNotExist as exc:
            raise CommandError(f'Company "{options["company"]}" was not found.') from exc

        with transaction.atomic():
            demo_products = Product.objects.filter(company=company).filter(
                Q(sku__startswith=DEMO_PREFIX) | Q(description=DEMO_MARKER)
            )
            if options['clear']:
                deleted_count = demo_products.count()
                demo_products.delete()
                self.stdout.write(self.style.SUCCESS(
                    f'Deleted {deleted_count} demo products for {company.name}.'
                ))
                return
            if options['reset']:
                demo_products.delete()

            supplier, _ = Counterparty.objects.get_or_create(
                company=company,
                name='Demo stock supplier',
                defaults={'type': 'china', 'is_supplier': True},
            )
            if not supplier.is_supplier:
                supplier.is_supplier = True
                supplier.save(update_fields=['is_supplier', 'updated_at'])
            unit, _ = Unit.objects.get_or_create(company=company, name='m')
            stock_settings = company_stock_settings(company)
            lead_days = Decimal(stock_settings.stock_delivery_lead_days)
            order_monthly = (Decimal('40') * Decimal('30') / lead_days).quantize(Decimal('0.01'))
            incoming_monthly = (Decimal('30') * Decimal('30') / lead_days).quantize(Decimal('0.01'))

            scenarios = (
                ('2099-17', 'Тюль премиум 2099-17 (тест)', '0', '0', '50', 'manual', '20', '50', 'OUT'),
                ('2099-21', 'Тюль премиум 2099-21 (тест)', '40', '0', '50', 'manual', '20', '50', 'BELOW'),
                ('DCD16-91', 'Ткань декоративная DCD16-91 (тест)', '120', '0', '100', 'manual', order_monthly, '50', 'ORDER'),
                ('IBG5036-92', 'BG Home IBG5036-92 (тест)', '120', '50', '100', 'manual', incoming_monthly, '50', 'INCOMING'),
                ('IBG5036-93', 'BG Home IBG5036-93 (тест)', '300', '0', '100', 'automatic', None, '50', 'NORMAL'),
                ('OY66-91', 'Ткань портьерная OY66-91 (тест)', '300', '0', '100', 'automatic', None, '50', 'GROWING'),
                ('5819-91', 'Kabuwanhao 5819-91 (тест)', '100', '0', '20', 'automatic', None, '50', 'NEW'),
            )

            products = {}
            for sku, name, on_hand, expected, minimum, mode, monthly, batch, scenario in scenarios:
                product, _ = Product.objects.update_or_create(
                    company=company,
                    sku=sku,
                    defaults={
                        'name': name,
                        'description': DEMO_MARKER,
                        'supplier': supplier,
                        'unit': unit,
                        'is_stock_item': True,
                        'is_archived': False,
                        'minimum_stock_level': Decimal(minimum),
                        'consumption_calculation_mode': mode,
                        'average_monthly_consumption': Decimal(monthly) if monthly else None,
                        'purchase_batch_size': Decimal(batch),
                    },
                )
                products[scenario] = product
                WarehouseStock.objects.update_or_create(
                    company=company,
                    product=product,
                    defaults={
                        'quantity_on_hand': Decimal(on_hand),
                        'quantity_reserved': Decimal('0.00'),
                        'quantity_expected': Decimal(expected),
                    },
                )

            now = timezone.now()
            old_product_ids = [products['NORMAL'].id, products['GROWING'].id]
            Product.objects.filter(id__in=old_product_ids).update(created_at=now - timedelta(days=200))
            Product.objects.filter(id=products['NEW'].id).update(created_at=now - timedelta(days=9))

            StockMovement.objects.filter(
                company=company,
                source_type='stock_control_demo',
            ).delete()
            for suffix in ('NORMAL', 'GROWING'):
                quantities = (
                    ('20', '20', '20', '20', '20', '20')
                    if suffix == 'NORMAL'
                    else ('60', '10', '10', '10', '10', '10')
                )
                for index, (days_ago, quantity) in enumerate(zip((15, 45, 75, 105, 135, 165), quantities)):
                    movement = StockMovement.objects.create(
                        company=company,
                        product=products[suffix],
                        movement_type=StockMovement.TYPE_CUSTOMER_SHIPPED,
                        quantity=Decimal(quantity),
                        source_type='stock_control_demo',
                        source_key=f'stock-control-demo:{company.id}:{suffix}:{index}',
                        comment='Generated warehouse-control history.',
                    )
                    StockMovement.objects.filter(pk=movement.pk).update(
                        created_at=now - timedelta(days=days_ago),
                    )

            rows = []
            for stock in WarehouseStock.objects.filter(
                company=company,
                product__description=DEMO_MARKER,
            ).select_related('product', 'product__unit').order_by('product__sku'):
                sync_critical_stock_alert(stock)
                rows.append(stock_control_item(stock, stock_settings))

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(rows)} demo products for {company.name}. '
            f'History window: {stock_settings.stock_consumption_history_days} days.'
        ))
        for row in rows:
            self.stdout.write(
                f'{row["sku"]}: {row["status_label"]}; '
                f'forecast={row["forecast_quality_label"]}; '
                f'monthly={row["average_monthly_consumption"] or "-"}; '
                f'recommended={row["recommended_order_quantity"] or "-"}'
            )
