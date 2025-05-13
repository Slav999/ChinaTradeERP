from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Counterparty, CounterpartyStatus, CounterpartyChangeLog
from .serializers import CounterpartySerializer, CounterpartyStatusSerializer, CounterpartyChangeLogSerializer


class CounterpartyViewSet(viewsets.ModelViewSet):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # фильтр только по компании
        return Counterparty.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
            updated_by=self.request.user
        )

    @transaction.atomic
    def perform_update(self, serializer):
        # сохраняем старый снимок
        instance = self.get_object()
        old = Counterparty.objects.get(pk=instance.pk)
        # выполняем обновление
        updated = serializer.save(updated_by=self.request.user)

        # для каждого поля, которое нужно отслеживать:
        for field in ['name', 'type', 'address', 'phone', 'email', 'source', 'status_id', 'qr_code_image']:
            old_val = getattr(old, field)
            new_val = getattr(updated, field)
            if field == 'qr_code_image':
                old_val = old_val.name if old_val else ''
                new_val = new_val.name if new_val else ''
            if old_val != new_val:
                CounterpartyChangeLog.objects.create(
                    counterparty=updated,
                    field_name=field,
                    old_value=str(old_val) if old_val is not None else '',
                    new_value=str(new_val) if new_val is not None else '',
                    changed_by=self.request.user
                )

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        cp = self.get_object()
        logs = cp.history.all()
        serializer = CounterpartyChangeLogSerializer(logs, many=True)
        return Response(serializer.data)


class CounterpartyStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CounterpartyStatus.objects.all()
    serializer_class = CounterpartyStatusSerializer
