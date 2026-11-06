from rest_framework import serializers
from django.utils import timezone


class AuditFieldsMixinSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)


class ChangeLogBaseSerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField()
    changed_at = serializers.SerializerMethodField()

    class Meta:
        fields = ['field_name', 'old_value', 'new_value', 'changed_by', 'changed_at']

    def get_changed_at(self, obj):
        return timezone.localtime(obj.changed_at).strftime("%Y-%m-%d %H:%M")
