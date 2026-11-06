from rest_framework import serializers
from .models import Counterparty, CounterpartyStatus, CounterpartyChangeLog
from core.serializers import AuditFieldsMixinSerializer, ChangeLogBaseSerializer
from core.statuses import TranslatableStatusSerializerMixin

class CounterpartyStatusSerializer(TranslatableStatusSerializerMixin, serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = CounterpartyStatus
        fields = '__all__'
        read_only_fields = ('company', 'code', 'is_system')
        extra_kwargs = {'name': {'required': False}}

    def validate_name(self, value):
        name = value.strip()
        request = self.context.get('request')
        queryset = CounterpartyStatus.objects.filter(name__iexact=name)
        if request and request.user.is_authenticated:
            queryset = queryset.filter(company=request.user.company)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Status already exists.')
        return name


class CounterpartySerializer(serializers.ModelSerializer, AuditFieldsMixinSerializer):
    qr_code_image = serializers.ImageField(required=False, allow_null=True)
    unique_code = serializers.CharField(required=False, allow_blank=True)
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
        read_only_fields = ('company',)

    def validate(self, attrs):
        request = self.context.get('request')
        status = attrs.get('status', getattr(self.instance, 'status', None))
        if request and request.user.is_authenticated and status and status.company_id != request.user.company_id:
            raise serializers.ValidationError({'status_id': 'Selected status is not available for your company.'})
        is_supplier = attrs.get('is_supplier', getattr(self.instance, 'is_supplier', False))
        is_customer = attrs.get('is_customer', getattr(self.instance, 'is_customer', False))
        if not is_supplier and not is_customer:
            raise serializers.ValidationError('Select at least one role: supplier or customer.')
        return attrs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            self.fields['status_id'].queryset = CounterpartyStatus.objects.filter(company=request.user.company)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('qr_code_image') and getattr(instance, 'updated_at', None):
            separator = '&' if '?' in data['qr_code_image'] else '?'
            data['qr_code_image'] = (
                f"{data['qr_code_image']}{separator}v={int(instance.updated_at.timestamp())}"
            )
        return data


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('qr_code_image') and getattr(instance, 'updated_at', None):
            separator = '&' if '?' in data['qr_code_image'] else '?'
            data['qr_code_image'] = (
                f"{data['qr_code_image']}{separator}v={int(instance.updated_at.timestamp())}"
            )
        return data


class CounterpartyOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counterparty
        fields = ('id', 'name', 'type', 'is_supplier', 'is_customer', 'unique_code')


class CounterpartyChangeLogSerializer(ChangeLogBaseSerializer):
    class Meta(ChangeLogBaseSerializer.Meta):
        model = CounterpartyChangeLog
