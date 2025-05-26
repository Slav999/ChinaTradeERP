
from rest_framework.permissions import IsAuthenticated
from counterparties.models import Counterparty, CounterpartyStatus, CounterpartyChangeLog
from counterparties.serializers import (
    CounterpartySerializer,
    CounterpartyStatusSerializer,
    CounterpartyChangeLogSerializer,
)
from core.views import BaseAuditViewSet, ChangeLogHistoryMixin
from rest_framework import viewsets


class CounterpartyViewSet(BaseAuditViewSet, ChangeLogHistoryMixin):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Counterparty.objects.filter(company=self.request.user.company)

    def get_serializer_class(self):
        if self.action == 'history':
            return CounterpartyChangeLogSerializer
        return super().get_serializer_class()

    def log_changes(self, old, new):
        fields = ['name', 'type', 'address', 'phone', 'email', 'source', 'status_id', 'qr_code_image']
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
