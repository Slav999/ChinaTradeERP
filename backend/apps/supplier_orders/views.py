from core.order_analytics import analytics_response
from core.order_reports import build_order_report
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from .models import (SupplierOrder, SupplierOrderStatus, SupplierOrderChangeLog, SupplierOrderAttachment,
                     SupplierOrderItem)
from .serializers import (
    SupplierOrderSerializer,
    SupplierOrderListSerializer,
    SupplierOrderStatusSerializer,
    SupplierOrderChangeLogSerializer,
    SupplierOrderItemSerializer,
    SupplierOrderAttachmentSerializer
)
from core.pagination import StandardResultsSetPagination
from core.order_documents import build_supplier_order_pdf
from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from django.http import FileResponse
from customer_orders.services.create_supplier_orders import build_supplier_order_related_documents
from warehouse.services import sync_customer_order, sync_supplier_order
from users.access import user_has_permission


def _require_permission(user, code):
    if not user_has_permission(user, code):
        raise PermissionDenied('You do not have permission to perform this action.')


class SupplierOrderViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = SupplierOrder.objects.all()
    serializer_class = SupplierOrderSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        code = 'orders.supplier.view' if request.method in ('GET', 'HEAD', 'OPTIONS') else 'orders.supplier.manage'
        _require_permission(request.user, code)

    def get_queryset(self):
        user_company = self.request.user.company
        queryset = SupplierOrder.objects.filter(
            company=user_company
        ).select_related(
            'supplier', 'customer', 'status', 'company', 'customer_order', 'company'
        )

        # Partition lists and exports; detail endpoints keep working for both kinds.
        if self.action in ('list', 'export'):
            is_sample = self.request.query_params.get('is_sample', '').lower() in ('true', '1')
            queryset = queryset.filter(is_sample=is_sample)
        trip_name = self.request.query_params.get('trip_name', '').strip()
        if trip_name:
            queryset = queryset.filter(trip_name__icontains=trip_name)

        search = self.request.query_params.get('search', '').strip()
        supplier_id = self.request.query_params.get('supplier')
        supplier_query = self.request.query_params.get('supplier_query', '').strip()
        customer_id = self.request.query_params.get('customer')
        customer_query = self.request.query_params.get('customer_query', '').strip()
        status_id = self.request.query_params.get('status')

        if search:
            queryset = queryset.filter(
                Q(trip_name__icontains=search) |
                Q(order_number__icontains=search) |
                Q(supplier__name__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(track_number__icontains=search) |
                Q(shipping_code__icontains=search) |
                Q(items__product__sku__icontains=search)
            ).distinct()
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if supplier_query:
            queryset = queryset.filter(supplier__name__icontains=supplier_query)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if customer_query:
            queryset = queryset.filter(customer__name__icontains=customer_query)
        if status_id:
            queryset = queryset.filter(status_id=status_id)

        return queryset

    @action(detail=False, methods=['get'], url_path='analytics')
    def analytics(self, request):
        _require_permission(request.user, 'reports.financial.view')
        return analytics_response(request, SupplierOrder, 'supplier')

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        orders = self.filter_queryset(self.get_queryset())
        buffer = build_order_report(
            orders,
            request.query_params,
            request.user.company,
            'supplier',
            include_financial=user_has_permission(request.user, 'pricing.purchase.view'),
        )

        return FileResponse(
            buffer,
            as_attachment=True,
            filename='supplier_orders.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    @action(detail=True, methods=['delete'], url_path=r'attachments/(?P<att_id>[^/.]+)')
    def delete_attachment(self, request, pk=None, att_id=None):
        order = self.get_object()
        try:
            att = order.attachments.get(pk=att_id)
        except SupplierOrderAttachment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        filename = att.file.name
        att.delete()
        # логируем удаление
        SupplierOrderChangeLog.objects.create(
            supplier_order=order,
            field_name='attachment',
            old_value=filename,
            new_value='',
            changed_by=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        _require_permission(request.user, 'pricing.purchase.manage')
        order = self.get_object()
        if not order.items.exists():
            return Response(
                {'detail': 'Add at least one position before sending the order.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


        # 1) Generate PDF in memory
        pdf_data = build_supplier_order_pdf(order)

        # 2) Берём email поставщика
        supplier_email = getattr(order.supplier, 'email', None)
        if not supplier_email:
            return Response(
                {"detail": "У поставщика не задан email."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3) Формируем и шлём письмо
        subject = f"Order #{order.order_number} from {request.user.company.name}"
        body = "Во вложении PDF с вашим заказом."
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[supplier_email],
            reply_to=[order.company.work_email] if order.company.work_email else None,
        )
        email.attach(f"order_{order.id}.pdf", pdf_data, "application/pdf")
        email.send(fail_silently=False)

        order.sent_at = timezone.now()
        order.updated_by = request.user
        order.save(update_fields=['sent_at', 'updated_by', 'updated_at'])

        return Response(
            {"status": "sent", "sent_at": order.sent_at},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], url_path='related-documents')
    def related_documents(self, request, pk=None):
        order = self.get_object()
        return Response(build_supplier_order_related_documents(
            order,
            include_customer_financial=user_has_permission(request.user, 'pricing.sale.view'),
            include_supplier_financial=user_has_permission(request.user, 'pricing.purchase.view'),
        ))

    def get_serializer_class(self):
        if self.action == 'history':
            return SupplierOrderChangeLogSerializer
        if self.action == 'list':
            return SupplierOrderListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        order = serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        sync_supplier_order(order, self.request.user)
        if order.customer_order_id:
            sync_customer_order(order.customer_order, self.request.user)

    def perform_update(self, serializer):
        obj = self.get_object()
        order = serializer.save(updated_by=self.request.user)
        self.log_changes(obj, order)
        sync_supplier_order(order, self.request.user)
        if order.customer_order_id:
            sync_customer_order(order.customer_order, self.request.user)

    def perform_destroy(self, instance):
        customer_order = instance.customer_order
        instance.delete()
        sync_supplier_order(instance, self.request.user)
        if customer_order:
            sync_customer_order(customer_order, self.request.user)


class SupplierOrderItemViewSet(viewsets.ModelViewSet):
    queryset = SupplierOrderItem.objects.all()
    serializer_class = SupplierOrderItemSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            _require_permission(request.user, 'orders.supplier.view')
            return
        _require_permission(request.user, 'orders.supplier.manage')
        if request.method in ('POST', 'PUT', 'PATCH'):
            _require_permission(request.user, 'pricing.purchase.manage')

    def get_queryset(self):
        user_company = self.request.user.company
        queryset = self.queryset.filter(
            order__company=user_company
        ).select_related('order', 'product', 'product__unit')

        order_id = self.request.query_params.get('order')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset

    def perform_create(self, serializer):
        item = serializer.save()
        sync_supplier_order(item.order, self.request.user)
        if item.order.customer_order_id:
            sync_customer_order(item.order.customer_order, self.request.user)

    def perform_update(self, serializer):
        old_price = serializer.instance.unit_price_cny
        item = serializer.save()
        if old_price != item.unit_price_cny:
            SupplierOrderChangeLog.objects.create(
                supplier_order=item.order,
                field_name='item_unit_price_cny',
                old_value=f'{item.product.sku}: {old_price}',
                new_value=f'{item.product.sku}: {item.unit_price_cny}',
                changed_by=self.request.user,
            )
        sync_supplier_order(item.order, self.request.user)
        if item.order.customer_order_id:
            sync_customer_order(item.order.customer_order, self.request.user)

    def perform_destroy(self, instance):
        order = instance.order
        customer_order = order.customer_order
        instance.delete()
        sync_supplier_order(order, self.request.user)
        if customer_order:
            sync_customer_order(customer_order, self.request.user)


class SupplierOrderStatusViewSet(viewsets.ModelViewSet):
    queryset = SupplierOrderStatus.objects.all()
    serializer_class = SupplierOrderStatusSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _require_permission(request.user, 'orders.supplier.view')
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can change statuses.')

    def get_queryset(self):
        return SupplierOrderStatus.objects.filter(company=self.request.user.company).order_by('id')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_company_admin:
            return Response({'detail': 'Only company admins can delete statuses.'}, status=status.HTTP_403_FORBIDDEN)
        if SupplierOrder.objects.filter(company=request.user.company, status=instance).exists():
            return Response({'detail': 'Status is used by supplier orders and cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)
