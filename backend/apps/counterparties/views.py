from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Counterparty, CounterpartyStatus
from .serializers import CounterpartySerializer, CounterpartyStatusSerializer


class CounterpartyViewSet(viewsets.ModelViewSet):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    permission_classes = [IsAuthenticated]


class CounterpartyStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CounterpartyStatus.objects.all()
    serializer_class = CounterpartyStatusSerializer
