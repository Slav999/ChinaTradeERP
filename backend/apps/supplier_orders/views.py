from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from .models import (SupplierOrder, SupplierOrderStatus, SupplierOrderChangeLog, SupplierOrderAttachment,
                     SupplierOrderItem)
from .serializers import (
    SupplierOrderSerializer,
    SupplierOrderStatusSerializer,
    SupplierOrderChangeLogSerializer,
    SupplierOrderItemSerializer,
    SupplierOrderAttachmentSerializer
)
import io
from django.conf import settings
from django.core.mail import EmailMessage
from reportlab.pdfgen import canvas
from rest_framework import status
from django.db.models import Q
import pandas as pd
from django.http import FileResponse
from customer_orders.services.create_supplier_orders import build_supplier_order_related_documents


class SupplierOrderViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = SupplierOrder.objects.all()
    serializer_class = SupplierOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_company = self.request.user.company
        return SupplierOrder.objects.filter(
            Q(supplier__company=user_company) |
            Q(customer__company=user_company)
        )

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        # 1) Получаем queryset (фильтры, права уже применены)
        orders = self.get_queryset()

        # 2) Собираем список словарей
        data = []
        for o in orders:
            data.append({
                'Order#': o.order_number,
                'Customer': o.customer.name if o.customer else '',
                'Supplier': o.supplier.name if o.supplier else '',
                'Shipping Address': o.shipping_address,
                'Shipment Time': o.shipment_date,
                'Status': o.status.name if o.status else '',
                'Code#': o.shipping_code,
            })

        # 3) pandas → Excel в память
        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Orders')
        buffer.seek(0)

        # 4) Отдаём как attachment
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
        order = self.get_object()

        # 1) Генерируем PDF в памяти
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.setFont("Helvetica", 14)
        p.drawString(50, 800, f"Order #{order.order_number}")
        y = 770
        p.setFont("Helvetica", 12)
        items = SupplierOrderItem.objects.filter(order=order)
        for idx, item in enumerate(items, start=1):
            line = f"{idx}. {item.product.name} — qty: {item.quantity}"
            p.drawString(50, y, line)
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
        p.showPage()
        p.save()
        buffer.seek(0)
        pdf_data = buffer.read()

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
        )
        email.attach(f"order_{order.id}.pdf", pdf_data, "application/pdf")
        email.send(fail_silently=False)

        return Response({"status": "sent"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='related-documents')
    def related_documents(self, request, pk=None):
        order = self.get_object()
        return Response(build_supplier_order_related_documents(order))

    def get_serializer_class(self):
        if self.action == 'history':
            return SupplierOrderChangeLogSerializer
        return super().get_serializer_class()


class SupplierOrderItemViewSet(viewsets.ModelViewSet):
    queryset = SupplierOrderItem.objects.all()
    serializer_class = SupplierOrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        order_id = self.request.query_params.get('order')
        if order_id:
            return self.queryset.filter(
                order_id=order_id,
                order__supplier__company=self.request.user.company
            )
        return self.queryset


class SupplierOrderStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupplierOrderStatus.objects.all()
    serializer_class = SupplierOrderStatusSerializer
    permission_classes = [IsAuthenticated]
