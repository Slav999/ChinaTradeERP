from rest_framework import serializers
from .models import Counterparty, CounterpartyStatus, CounterpartyChangeLog
from core.serializers import AuditFieldsMixinSerializer, ChangeLogBaseSerializer

class CounterpartyStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterpartyStatus
        fields = '__all__'


class CounterpartySerializer(serializers.ModelSerializer, AuditFieldsMixinSerializer):
    qr_code_image = serializers.ImageField(required=False, allow_null=True)
    status = CounterpartyStatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=CounterpartyStatus.objects.all(),
        source='status',
        write_only=True,
        required=False,
        allow_null=True
    )
    company_id = serializers.PrimaryKeyRelatedField(source='company', read_only=True)

    class Meta:
        model = Counterparty
        fields = '__all__'


class CounterpartyChangeLogSerializer(ChangeLogBaseSerializer):
    class Meta(ChangeLogBaseSerializer.Meta):
        model = CounterpartyChangeLog