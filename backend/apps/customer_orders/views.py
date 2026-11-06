from core.order_analytics import analytics_response
from core.order_reports import build_order_report
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from .models import (
    CustomerOrder,
    CustomerOrderStatus,
    CustomerOrderChangeLog,
    CustomerOrderAttachment,
    CustomerOrderItem
)
from .serializers import (
    CustomerOrderSerializer,
    CustomerOrderListSerializer,
    CustomerOrderStatusSerializer,
    CustomerOrderChangeLogSerializer,
    CustomerOrderItemSerializer,
    CustomerOrderAttachmentSerializer
)
from core.pagination import StandardResultsSetPagination
from core.order_documents import build_customer_order_pdf
from .services.create_supplier_orders import (
    SupplierOrderCreationError,
    build_customer_order_related_documents,
    create_supplier_orders_for_customer_order,
    supplier_order_card,
)
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
from django.utils import timezone
from django.http import FileResponse
from warehouse.services import sync_customer_order
from users.access import user_has_permission


def _require_permission(user, code):
    if not user_has_permission(user, code):
        raise PermissionDenied('You do not have permission to perform this action.')


class CustomerOrderViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = CustomerOrder.objects.all()
    serializer_class = CustomerOrderSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        code = 'orders.customer.view' if request.method in ('GET', 'HEAD', 'OPTIONS') else 'orders.customer.manage'
        _require_permission(request.user, code)

    def get_queryset(self):
        user_company = self.request.user.company
        queryset = CustomerOrder.objects.filter(
            company=user_company
        ).select_related(
            'customer', 'status', 'company'
        )

        search = self.request.query_params.get('search', '').strip()
        customer_id = self.request.query_params.get('customer')
        customer_query = self.request.query_params.get('customer_query', '').strip()
        status_id = self.request.query_params.get('status')

        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(shipping_code__icontains=search) |
                Q(items__product__sku__icontains=search)
            ).distinct()
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
        return analytics_response(request, CustomerOrder, 'customer')

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        orders = self.filter_queryset(self.get_queryset())
        buffer = build_order_report(
            orders,
            request.query_params,
            request.user.company,
            'customer',
            include_financial=user_has_permission(request.user, 'pricing.sale.view'),
        )

        return FileResponse(
            buffer,
            as_attachment=True,
            filename='customer_orders.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    @action(detail=True, methods=['delete'], url_path=r'attachments/(?P<att_id>[^/.]+)')
    def delete_attachment(self, request, pk=None, att_id=None):
        order = self.get_object()
        try:
            att = order.attachments.get(pk=att_id)
        except CustomerOrderAttachment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        filename = att.file.name
        att.delete()
        # log deletion
        CustomerOrderChangeLog.objects.create(
            customer_order=order,
            field_name='attachment',
            old_value=filename,
            new_value='',
            changed_by=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        _require_permission(request.user, 'pricing.sale.order.manage')
        order = self.get_object()
        if not order.items.exists():
            return Response(
                {'detail': 'Add at least one position before sending the order.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


        # 1) Generate PDF in memory
        pdf_data = build_customer_order_pdf(order)

        # 2) Get customer's email
        customer_email = getattr(order.customer, 'email', None)
        if not customer_email:
            return Response(
                {"detail": "Customer email is not set."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3) Build and send email
        subject = f"Order #{order.order_number} from {request.user.company.name}"
        body = "Please find attached the PDF of your order."
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer_email],
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

    @action(detail=True, methods=['post'], url_path='create-supplier-orders')
    def create_supplier_orders(self, request, pk=None):
        _require_permission(request.user, 'orders.supplier.manage')
        _require_permission(request.user, 'pricing.purchase.manage')
        order = self.get_object()
        try:
            result = create_supplier_orders_for_customer_order(order, request.user)
        except SupplierOrderCreationError as exc:
            return Response({'detail': exc.detail}, status=exc.status_code)

        created_orders = result['created']
        updated_orders = result['updated']
        response_status = (
            status.HTTP_201_CREATED if created_orders else status.HTTP_200_OK
        )
        return Response(
            {
                'count': len(created_orders) + len(updated_orders),
                'created': [supplier_order_card(
                    order,
                    include_financial=user_has_permission(request.user, 'pricing.purchase.view'),
                ) for order in created_orders],
                'updated': [supplier_order_card(
                    order,
                    include_financial=user_has_permission(request.user, 'pricing.purchase.view'),
                ) for order in updated_orders],
            },
            status=response_status,
        )

    @action(detail=True, methods=['get'], url_path='supplier-orders')
    def supplier_orders(self, request, pk=None):
        _require_permission(request.user, 'orders.supplier.view')
        order = self.get_object()
        data = build_customer_order_related_documents(
            order,
            include_customer_financial=user_has_permission(request.user, 'pricing.sale.view'),
            include_supplier_financial=user_has_permission(request.user, 'pricing.purchase.view'),
        )
        return Response(data['children'])

    @action(detail=True, methods=['get'], url_path='related-documents')
    def related_documents(self, request, pk=None):
        order = self.get_object()
        can_view_supplier_orders = user_has_permission(request.user, 'orders.supplier.view')
        return Response(build_customer_order_related_documents(
            order,
            include_customer_financial=user_has_permission(request.user, 'pricing.sale.view'),
            include_supplier_financial=(
                can_view_supplier_orders and user_has_permission(request.user, 'pricing.purchase.view')
            ),
            include_supplier_orders=can_view_supplier_orders,
        ))

    def get_serializer_class(self):
        if self.action == 'history':
            return CustomerOrderChangeLogSerializer
        if self.action == 'list':
            return CustomerOrderListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        order = serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        sync_customer_order(order, self.request.user)

    def perform_update(self, serializer):
        obj = self.get_object()
        order = serializer.save(updated_by=self.request.user)
        self.log_changes(obj, order)
        sync_customer_order(order, self.request.user)


class CustomerOrderItemViewSet(viewsets.ModelViewSet):
    queryset = CustomerOrderItem.objects.all()
    serializer_class = CustomerOrderItemSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            _require_permission(request.user, 'orders.customer.view')
            return
        _require_permission(request.user, 'orders.customer.manage')
        if request.method in ('POST', 'PUT', 'PATCH'):
            _require_permission(request.user, 'pricing.sale.order.manage')

    def get_queryset(self):
        queryset = self.queryset.filter(
            order__company=self.request.user.company
        ).select_related('order', 'product', 'product__unit')

        order_id = self.request.query_params.get('order')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset

    def perform_create(self, serializer):
        item = serializer.save()
        sync_customer_order(item.order, self.request.user)

    def perform_update(self, serializer):
        old_price = serializer.instance.unit_sale_price
        item = serializer.save()
        if old_price != item.unit_sale_price:
            CustomerOrderChangeLog.objects.create(
                customer_order=item.order,
                field_name='item_unit_sale_price',
                old_value=f'{item.product.sku}: {old_price}',
                new_value=f'{item.product.sku}: {item.unit_sale_price}',
                changed_by=self.request.user,
            )
        sync_customer_order(item.order, self.request.user)

    def perform_destroy(self, instance):
        order = instance.order
        instance.delete()
        sync_customer_order(order, self.request.user)


class CustomerOrderStatusViewSet(viewsets.ModelViewSet):
    queryset = CustomerOrderStatus.objects.all()
    serializer_class = CustomerOrderStatusSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _require_permission(request.user, 'orders.customer.view')
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can change statuses.')

    def get_queryset(self):
        return CustomerOrderStatus.objects.filter(company=self.request.user.company).order_by('id')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_company_admin:
            return Response({'detail': 'Only company admins can delete statuses.'}, status=status.HTTP_403_FORBIDDEN)
        if CustomerOrder.objects.filter(company=request.user.company, status=instance).exists():
            return Response({'detail': 'Status is used by customer orders and cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)
