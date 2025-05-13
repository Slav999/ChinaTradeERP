from rest_framework import serializers
from .models import Counterparty, CounterpartyStatus, CounterpartyChangeLog


class CounterpartyStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterpartyStatus
        fields = '__all__'


class CounterpartySerializer(serializers.ModelSerializer):
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
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Counterparty
        fields = '__all__'


class CounterpartyChangeLogSerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField()
    changed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")

    class Meta:
        model = CounterpartyChangeLog
        fields = ['field_name', 'old_value', 'new_value', 'changed_by', 'changed_at']