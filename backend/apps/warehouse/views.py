from django.http import FileResponse
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4
from django.db import transaction
from django.utils.dateparse import parse_date
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import F, Q

from core.pagination import StandardResultsSetPagination
from supplier_orders.models import SupplierOrderItem
from .models import (
    StockAlert,
    StockAlertDismissal,
    StockControlDismissal,
    StockControlSnapshot,
    StockMovement,
    WarehouseStock,
)
from .reporting import build_stock_control_workbook, build_warehouse_report_workbook, warehouse_summary_rows
from .serializers import (
    StockControlSnapshotSerializer,
    StockAlertSerializer,
    StockMovementSerializer,
    WarehouseReportFilterSerializer,
    WarehouseOperationSerializer,
    WarehouseStockSerializer,
)
from .services import recalculate_product_stock
from .stock_control import (
    company_local_date,
    company_stock_settings,
    ensure_due_stock_control_snapshot,
    generate_stock_control_snapshot,
    live_stock_control_data,
    stock_control_rows,
)
from users.access import user_has_permission


def _require_warehouse_permission(user, *, manage=False):
    code = 'warehouse.manage' if manage else 'warehouse.view'
    if not user_has_permission(user, code):
        raise PermissionDenied('You do not have permission to access the warehouse.')


class WarehouseStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WarehouseStockSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _require_warehouse_permission(request.user, manage=self.action == 'operation')

    def get_queryset(self):
        queryset = WarehouseStock.objects.filter(
            company=self.request.user.company,
            product__is_stock_item=True,
            product__is_archived=False,
        ).select_related('product', 'product__category', 'product__unit', 'product__supplier')
        search = self.request.query_params.get('search', '').strip()
        category_id = self.request.query_params.get('category')
        category_query = self.request.query_params.get('category_query', '').strip()
        supplier_id = self.request.query_params.get('supplier')
        supplier_query = self.request.query_params.get('supplier_query', '').strip()
        only_available = self.request.query_params.get('only_available')
        stock_control = self.request.query_params.get('stock_control', '').strip()
        date_from = parse_date(self.request.query_params.get('date_from', ''))
        date_to = parse_date(self.request.query_params.get('date_to', ''))
        if search:
            queryset = queryset.filter(
                Q(product__name__icontains=search) |
                Q(product__sku__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        if category_query:
            queryset = queryset.filter(product__category__name__icontains=category_query)
        if supplier_id:
            queryset = queryset.filter(product__supplier_id=supplier_id)
        if supplier_query:
            queryset = queryset.filter(product__supplier__name__icontains=supplier_query)
        if only_available in ('1', 'true', 'True'):
            queryset = queryset.filter(quantity_on_hand__gt=F('quantity_reserved'))
        if stock_control in ('attention', 'no_forecast', 'normal'):
            attention_statuses = {
                'out_of_stock', 'below_minimum', 'requires_order', 'supply_expected',
            }
            rows = stock_control_rows(self.request.user.company)
            if stock_control == 'attention':
                product_ids = [
                    row['product_id'] for row in rows
                    if row['status'] in attention_statuses
                ]
            elif stock_control == 'no_forecast':
                product_ids = [
                    row['product_id'] for row in rows
                    if not row['has_consumption_data']
                ]
            else:
                product_ids = [
                    row['product_id'] for row in rows
                    if row['status'] == stock_control
                ]
            queryset = queryset.filter(product_id__in=product_ids)
        if date_from or date_to:
            supplier_items = SupplierOrderItem.objects.filter(
                order__company=self.request.user.company,
                order__customer_order__isnull=True,
                product__is_stock_item=True,
                product__is_archived=False,
            )
            if date_from:
                supplier_items = supplier_items.filter(order__created_at__date__gte=date_from)
            if date_to:
                supplier_items = supplier_items.filter(order__created_at__date__lte=date_to)
            queryset = queryset.filter(product_id__in=supplier_items.values('product_id'))
        return queryset.order_by('product__name', 'product__sku')

    @action(detail=True, methods=['post'], url_path='operation')
    def operation(self, request, pk=None):
        serializer = WarehouseOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        with transaction.atomic():
            stock = WarehouseStock.objects.select_for_update().filter(
                pk=pk,
                company=request.user.company,
                product__is_stock_item=True,
            ).select_related('product').first()
            if not stock:
                return Response({'detail': 'Warehouse item not found.'}, status=status.HTTP_404_NOT_FOUND)

            operation = values['action']
            quantity = values['quantity']
            if operation in {
                WarehouseOperationSerializer.ACTION_RELEASE_DEFECT,
                WarehouseOperationSerializer.ACTION_WRITE_OFF_DEFECT,
            } and quantity > stock.quantity_defective:
                return Response(
                    {'quantity': 'Quantity exceeds defective stock.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if (
                operation == WarehouseOperationSerializer.ACTION_WRITE_OFF_STOCK
                and quantity > stock.quantity_available
            ):
                return Response(
                    {'quantity': 'Quantity exceeds available stock.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            movement_type = {
                WarehouseOperationSerializer.ACTION_RELEASE_DEFECT: StockMovement.TYPE_DEFECT_RELEASED,
                WarehouseOperationSerializer.ACTION_WRITE_OFF_DEFECT: StockMovement.TYPE_DEFECT_WRITTEN_OFF,
                WarehouseOperationSerializer.ACTION_WRITE_OFF_STOCK: StockMovement.TYPE_STOCK_WRITTEN_OFF,
            }[operation]
            reason = values.get('reason', '')
            comment = values.get('comment', '').strip()
            details = ' · '.join(part for part in (reason, comment) if part)
            StockMovement.objects.create(
                company=stock.company,
                product=stock.product,
                movement_type=movement_type,
                quantity=quantity,
                source_type='warehouse_operation',
                source_key=f'warehouse_operation:{uuid4().hex}',
                comment=details,
                created_by=request.user,
            )
            stock = recalculate_product_stock(stock.product)
        return Response(WarehouseStockSerializer(stock, context={'request': request}).data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _require_warehouse_permission(request.user)

    def get_queryset(self):
        queryset = StockMovement.objects.filter(
            company=self.request.user.company,
            product__is_stock_item=True,
        ).select_related('product', 'product__category', 'product__unit', 'product__supplier', 'created_by')
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset


class WarehouseReportExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_warehouse_permission(request.user)
        serializer = WarehouseReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        buffer = build_warehouse_report_workbook(
            request.user.company,
            serializer.validated_data,
            include_financial=user_has_permission(request.user, 'pricing.purchase.view'),
        )
        filename = f'warehouse_report_{timezone.localdate():%Y%m%d}.xlsx'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type=(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        )


class WriteOffReportExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .reporting import build_write_off_workbook
        _require_warehouse_permission(request.user)
        serializer = WarehouseReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        movements = StockMovement.objects.filter(company=request.user.company, movement_type__in=(
            StockMovement.TYPE_DEFECT_WRITTEN_OFF, StockMovement.TYPE_STOCK_WRITTEN_OFF,
        )).select_related('product', 'product__unit', 'created_by').order_by('-created_at', '-id')
        if filters.get('date_from'):
            movements = movements.filter(created_at__date__gte=filters['date_from'])
        if filters.get('date_to'):
            movements = movements.filter(created_at__date__lte=filters['date_to'])
        if filters.get('product_ids'):
            movements = movements.filter(product_id__in=filters['product_ids'])
        for key, lookup in (('search', 'product__name__icontains'),
                            ('supplier_query', 'product__supplier__name__icontains'),
                            ('category_query', 'product__category__name__icontains')):
            if filters.get(key):
                if key == 'search':
                    movements = movements.filter(Q(product__name__icontains=filters[key]) | Q(product__sku__icontains=filters[key]))
                else:
                    movements = movements.filter(**{lookup: filters[key]})
        ru = request.user.company.language_code != 'en'
        start, end = filters.get('date_from'), filters.get('date_to')
        if start and end:
            period = f'{start:%d.%m.%Y} — {end:%d.%m.%Y}'
        elif start:
            period = ('С ' if ru else 'From ') + start.strftime('%d.%m.%Y')
        elif end:
            period = ('По ' if ru else 'Through ') + end.strftime('%d.%m.%Y')
        else:
            period = 'За всё время' if ru else 'All time'
        filename = 'Отчёт по списаниям.xlsx' if ru else 'Write-off report.xlsx'
        return FileResponse(build_write_off_workbook(request.user.company, movements, period),
                            as_attachment=True, filename=filename,
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class WarehouseReportSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_warehouse_permission(request.user)
        serializer = WarehouseReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        include_financial = user_has_permission(request.user, 'pricing.purchase.view')
        if (
            not include_financial
            and serializer.validated_data.get('metric') in ('total_cny', 'total_local')
        ):
            raise PermissionDenied('You do not have permission to view financial stock metrics.')
        product_ids = serializer.validated_data.get('product_ids') or []
        if len(product_ids) > 20:
            return Response(
                {'detail': 'Select up to 20 products for the chart.'},
                status=400,
            )
        return Response(warehouse_summary_rows(
            request.user.company,
            serializer.validated_data,
            include_financial=include_financial,
        ))


class StockControlLatestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_warehouse_permission(request.user)
        settings = company_stock_settings(request.user.company)
        ensure_due_stock_control_snapshot(request.user.company, request.user)
        snapshot = StockControlSnapshot.objects.filter(
            company=request.user.company,
        ).prefetch_related('dismissals').first()
        if not snapshot:
            return Response({'snapshot': None, 'has_unread_attention': False})
        snapshot._dismissed_user_ids = {
            dismissal.user_id for dismissal in snapshot.dismissals.all()
        }
        data = StockControlSnapshotSerializer(snapshot, context={'request': request}).data
        return Response({
            'snapshot': data,
            'has_unread_attention': (
                settings.stock_weekly_control_enabled
                and data['summary'].get('attention_count', 0) > 0
                and not data['is_dismissed']
            ),
        })


class StockControlLiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_warehouse_permission(request.user)
        return Response(live_stock_control_data(request.user.company))


class StockControlLiveExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_warehouse_permission(request.user)
        data = live_stock_control_data(request.user.company)
        workbook_source = SimpleNamespace(**data)
        workbook_source.company = request.user.company
        buffer = build_stock_control_workbook(workbook_source)
        filename = f'stock_control_{data["schedule_date"]:%Y%m%d}.xlsx'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class StockAlertListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_warehouse_permission(request.user)
        alerts = StockAlert.objects.filter(
            company=request.user.company,
            resolved_at__isnull=True,
        ).exclude(
            dismissals__user=request.user,
        ).select_related('product', 'product__unit')[:20]
        return Response(StockAlertSerializer(alerts, many=True).data)


class StockAlertDismissView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        _require_warehouse_permission(request.user)
        alert = StockAlert.objects.filter(
            company=request.user.company,
            resolved_at__isnull=True,
            pk=pk,
        ).first()
        if not alert:
            return Response({'detail': 'Stock alert was not found.'}, status=404)
        StockAlertDismissal.objects.get_or_create(alert=alert, user=request.user)
        return Response({'dismissed': True})


def _notification_text(language, kind, payload):
    if language == 'en':
        if kind == 'stock_alert':
            if payload['available_quantity'] <= 0:
                return 'Out of stock', f'{payload["sku"]} · {payload["product_name"]} is out of stock.'
            return 'Stock below minimum', (
                f'{payload["sku"]} · {payload["product_name"]}: '
                f'{payload["available_quantity"]:g} available, minimum {payload["minimum_stock_level"]:g}.'
            )
        return 'Weekly stock control', (
            f'{payload["attention_count"]} products require attention: '
            f'{payload["out_of_stock_count"]} out of stock, '
            f'{payload["below_minimum_count"]} below minimum, '
            f'{payload["requires_order_count"]} require an order.'
        )
    if kind == 'stock_alert':
        if payload['available_quantity'] <= 0:
            return 'Товар закончился', f'{payload["sku"]} · {payload["product_name"]}: доступный остаток равен нулю.'
        return 'Остаток ниже минимума', (
            f'{payload["sku"]} · {payload["product_name"]}: '
            f'доступно {payload["available_quantity"]:g}, минимум {payload["minimum_stock_level"]:g}.'
        )
    return 'Еженедельный контроль остатков', (
        f'{payload["attention_count"]} товаров требуют внимания: '
        f'{payload["out_of_stock_count"]} закончились, '
        f'{payload["below_minimum_count"]} ниже минимума, '
        f'{payload["requires_order_count"]} требуют заказа.'
    )


class NotificationFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_warehouse_permission(request.user)
        company = request.user.company
        language = company.language_code or 'ru'
        history_cutoff = timezone.now() - timedelta(days=30)
        ensure_due_stock_control_snapshot(company, request.user)
        items = []

        alerts = StockAlert.objects.filter(company=company, created_at__gte=history_cutoff).select_related(
            'product', 'product__unit'
        ).prefetch_related('dismissals')[:40]
        for alert in alerts:
            user_dismissal = next(
                (dismissal for dismissal in alert.dismissals.all() if dismissal.user_id == request.user.id),
                None,
            )
            if user_dismissal and user_dismissal.hidden_at:
                continue
            payload = {
                'sku': alert.product.sku,
                'product_name': alert.product.name,
                'unit': alert.product.unit.name if alert.product.unit else '',
                'available_quantity': alert.available_quantity,
                'minimum_stock_level': alert.minimum_stock_level,
                'expected_quantity': alert.expected_quantity,
                'recommended_order_quantity': alert.recommended_order_quantity,
            }
            title, message = _notification_text(language, 'stock_alert', payload)
            is_read = alert.resolved_at is not None or user_dismissal is not None
            items.append({
                'key': f'stock_alert:{alert.id}',
                'kind': 'stock_alert',
                'source_id': alert.id,
                'severity': 'danger',
                'title': title,
                'message': message,
                'created_at': alert.created_at,
                'is_read': is_read,
                'is_resolved': alert.resolved_at is not None,
                'action': {'path': '/warehouse', 'query': {'stockControl': '1'}},
                'payload': payload,
            })

        snapshots = StockControlSnapshot.objects.filter(
            company=company,
            source=StockControlSnapshot.SOURCE_SCHEDULED,
            generated_at__gte=history_cutoff,
        ).prefetch_related('dismissals')[:20]
        for snapshot in snapshots:
            user_dismissal = next(
                (dismissal for dismissal in snapshot.dismissals.all() if dismissal.user_id == request.user.id),
                None,
            )
            if user_dismissal and user_dismissal.hidden_at:
                continue
            summary = snapshot.summary or {}
            if not summary.get('attention_count', 0):
                continue
            payload = {
                'attention_count': summary.get('attention_count', 0),
                'out_of_stock_count': summary.get('out_of_stock_count', 0),
                'below_minimum_count': summary.get('below_minimum_count', summary.get('critical_count', 0)),
                'requires_order_count': summary.get('requires_order_count', 0),
                'supply_expected_count': summary.get('supply_expected_count', 0),
                'schedule_date': snapshot.schedule_date.isoformat(),
            }
            title, message = _notification_text(language, 'stock_weekly', payload)
            is_read = user_dismissal is not None
            items.append({
                'key': f'stock_weekly:{snapshot.id}',
                'kind': 'stock_weekly',
                'source_id': snapshot.id,
                'severity': 'warning',
                'title': title,
                'message': message,
                'created_at': snapshot.generated_at,
                'is_read': is_read,
                'is_resolved': False,
                'action': {'path': '/warehouse', 'query': {'stockControl': '1'}},
                'payload': payload,
            })

        items.sort(key=lambda item: item['created_at'], reverse=True)
        items = items[:50]
        return Response({
            'unread_count': sum(1 for item in items if not item['is_read']),
            'results': items,
        })


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_warehouse_permission(request.user)
        kind = request.data.get('kind')
        source_id = request.data.get('source_id')
        if kind == 'stock_alert':
            source = StockAlert.objects.filter(company=request.user.company, pk=source_id).first()
            if not source:
                return Response({'detail': 'Notification was not found.'}, status=404)
            StockAlertDismissal.objects.get_or_create(alert=source, user=request.user)
        elif kind == 'stock_weekly':
            source = StockControlSnapshot.objects.filter(company=request.user.company, pk=source_id).first()
            if not source:
                return Response({'detail': 'Notification was not found.'}, status=404)
            StockControlDismissal.objects.get_or_create(snapshot=source, user=request.user)
        else:
            return Response({'detail': 'Unknown notification type.'}, status=400)
        return Response({'read': True})


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_warehouse_permission(request.user)
        alerts = StockAlert.objects.filter(company=request.user.company, resolved_at__isnull=True)
        StockAlertDismissal.objects.bulk_create(
            [StockAlertDismissal(alert=alert, user=request.user) for alert in alerts],
            ignore_conflicts=True,
        )
        snapshots = StockControlSnapshot.objects.filter(
            company=request.user.company,
            source=StockControlSnapshot.SOURCE_SCHEDULED,
        )[:20]
        StockControlDismissal.objects.bulk_create(
            [StockControlDismissal(snapshot=snapshot, user=request.user) for snapshot in snapshots],
            ignore_conflicts=True,
        )
        return Response({'read': True})


class NotificationHideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_warehouse_permission(request.user)
        kind = request.data.get('kind')
        source_id = request.data.get('source_id')
        if kind == 'stock_alert':
            source = StockAlert.objects.filter(company=request.user.company, pk=source_id).first()
            if not source:
                return Response({'detail': 'Notification was not found.'}, status=404)
            dismissal, _ = StockAlertDismissal.objects.get_or_create(alert=source, user=request.user)
        elif kind == 'stock_weekly':
            source = StockControlSnapshot.objects.filter(company=request.user.company, pk=source_id).first()
            if not source:
                return Response({'detail': 'Notification was not found.'}, status=404)
            dismissal, _ = StockControlDismissal.objects.get_or_create(snapshot=source, user=request.user)
        else:
            return Response({'detail': 'Unknown notification type.'}, status=400)
        dismissal.hidden_at = timezone.now()
        dismissal.save(update_fields=['hidden_at'])
        return Response({'hidden': True})


class StockControlGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_warehouse_permission(request.user, manage=True)
        settings = company_stock_settings(request.user.company)
        snapshot = generate_stock_control_snapshot(
            request.user.company,
            StockControlSnapshot.SOURCE_MANUAL,
            company_local_date(settings),
            request.user,
        )
        return Response(StockControlSnapshotSerializer(
            snapshot,
            context={'request': request},
        ).data)


class StockControlDismissView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        _require_warehouse_permission(request.user)
        snapshot = StockControlSnapshot.objects.filter(
            company=request.user.company,
            pk=pk,
        ).first()
        if not snapshot:
            return Response({'detail': 'Stock control report was not found.'}, status=404)
        StockControlDismissal.objects.get_or_create(snapshot=snapshot, user=request.user)
        return Response({'dismissed': True})


class StockControlExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_warehouse_permission(request.user)
        snapshot = StockControlSnapshot.objects.filter(
            company=request.user.company,
            pk=pk,
        ).first()
        if not snapshot:
            return Response({'detail': 'Stock control report was not found.'}, status=404)
        buffer = build_stock_control_workbook(snapshot)
        filename = f'stock_control_{snapshot.schedule_date:%Y%m%d}.xlsx'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
