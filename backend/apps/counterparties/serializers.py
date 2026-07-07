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

    def validate(self, attrs):
        is_supplier = attrs.get('is_supplier', getattr(self.instance, 'is_supplier', False))
        is_customer = attrs.get('is_customer', getattr(self.instance, 'is_customer', False))
        if not is_supplier and not is_customer:
            raise serializers.ValidationError('Select at least one role: supplier or customer.')
        return attrs


class CounterpartyListSerializer(AuditFieldsMixinSerializer, serializers.ModelSerializer):
    status = CounterpartyStatusSerializer(read_only=True)
    qr_code_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Counterparty
        fields = (
            'id', 'name', 'type', 'is_supplier', 'is_customer', 'unique_code', 'address',
            'phone', 'email', 'source', 'status', 'qr_code_image',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        )


class CounterpartyOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counterparty
        fields = ('id', 'name', 'type', 'is_supplier', 'is_customer', 'unique_code')


class CounterpartyChangeLogSerializer(ChangeLogBaseSerializer):
    class Meta(ChangeLogBaseSerializer.Meta):
        model = CounterpartyChangeLog
