
from rest_framework.permissions import IsAuthenticated
from counterparties.models import Counterparty, CounterpartyStatus, CounterpartyChangeLog
from counterparties.serializers import (
    CounterpartySerializer,
    CounterpartyListSerializer,
    CounterpartyOptionSerializer,
    CounterpartyStatusSerializer,
    CounterpartyChangeLogSerializer,
)
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from core.pagination import StandardResultsSetPagination
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q


class CounterpartyViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Counterparty.objects.filter(
            company=self.request.user.company
        ).select_related('status')

        search = self.request.query_params.get('search', '').strip()
        counterparty_type = self.request.query_params.get('type')
        role = self.request.query_params.get('role')
        status_id = self.request.query_params.get('status')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(unique_code__icontains=search) |
                Q(phone__icontains=search) |
                Q(source__icontains=search)
            )
        if counterparty_type:
            queryset = queryset.filter(type=counterparty_type)
        if role == 'supplier':
            queryset = queryset.filter(is_supplier=True)
        elif role == 'customer':
            queryset = queryset.filter(is_customer=True)
        if status_id:
            queryset = queryset.filter(status_id=status_id)

        return queryset.order_by('-created_at', '-id')

    def get_serializer_class(self):
        if self.action == 'history':
            return CounterpartyChangeLogSerializer
        if self.action == 'list':
            return CounterpartyListSerializer
        if self.action == 'options':
            return CounterpartyOptionSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        from customer_orders.models import CustomerOrder, CustomerOrderItem
        from products.models import Product
        from supplier_orders.models import SupplierOrder, SupplierOrderItem

        if CustomerOrder.objects.filter(company=request.user.company, customer=instance).exists():
            return Response(
                {'detail': 'Counterparty is used by customer orders and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if SupplierOrder.objects.filter(company=request.user.company).filter(
            Q(supplier=instance) | Q(customer=instance)
        ).exists():
            return Response(
                {'detail': 'Counterparty is used by supplier orders and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        products = Product.objects.filter(company=request.user.company, supplier=instance)
        if products.filter(is_archived=False).exists():
            return Response(
                {'detail': 'Counterparty is used by active products and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        archived_products = products.filter(is_archived=True)
        if CustomerOrderItem.objects.filter(product__in=archived_products).exists():
            return Response(
                {'detail': 'Counterparty is used by archived products from customer orders and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if SupplierOrderItem.objects.filter(product__in=archived_products).exists():
            return Response(
                {'detail': 'Counterparty is used by archived products from supplier orders and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        archived_products.delete()
        return super().destroy(request, *args, **kwargs)

    def log_changes(self, old, new):
        fields = ['name', 'type', 'is_supplier', 'is_customer', 'address', 'phone', 'email', 'source', 'status_id', 'qr_code_image']
        for field in fields:
            old_val = getattr(old, field)
            new_val = getattr(new, field)
            if field == 'qr_code_image':
                old_val = old_val.name if old_val else ''
                new_val = new_val.name if new_val else ''
            if old_val != new_val:
                CounterpartyChangeLog.objects.create(
                    counterparty=new,
                    field_name=field,
                    old_value=str(old_val or ''),
                    new_value=str(new_val or ''),
                    changed_by=self.request.user
                )


class CounterpartyStatusViewSet(viewsets.ModelViewSet):
    queryset = CounterpartyStatus.objects.all()
    serializer_class = CounterpartyStatusSerializer
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and not request.user.is_company_admin:
            raise PermissionDenied('Only company admins can change statuses.')

    def get_queryset(self):
        return CounterpartyStatus.objects.filter(company=self.request.user.company).order_by('name')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_company_admin:
            return Response({'detail': 'Only company admins can delete statuses.'}, status=status.HTTP_403_FORBIDDEN)
        if Counterparty.objects.filter(company=request.user.company, status=instance).exists():
            return Response({'detail': 'Status is used by counterparties and cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)
