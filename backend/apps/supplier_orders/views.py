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


class SupplierOrderViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = SupplierOrder.objects.all()
    serializer_class = SupplierOrderSerializer
    permission_classes = [IsAuthenticated]

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