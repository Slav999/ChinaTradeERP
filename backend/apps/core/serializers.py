from rest_framework import serializers


class AuditFieldsMixinSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)


class ChangeLogBaseSerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField()
    changed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")

    class Meta:
        fields = ['field_name', 'old_value', 'new_value', 'changed_by', 'changed_at']
