from rest_framework import serializers
from .models import Counterparty, CounterpartyStatus


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

    class Meta:
        model = Counterparty
        fields = '__all__'
