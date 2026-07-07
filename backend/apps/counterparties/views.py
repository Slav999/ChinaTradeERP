
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
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q


class CounterpartyViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Counterparty.objects.filter(
            company=self.request.user.company
        ).select_related('status').order_by('name')

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

        return queryset

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


class CounterpartyStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CounterpartyStatus.objects.all()
    serializer_class = CounterpartyStatusSerializer
