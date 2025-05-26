from rest_framework import viewsets
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response


class BaseAuditViewSet(viewsets.ModelViewSet):
    """
    Базовый ViewSet: автоматически проставляет created_by, updated_by, company (если есть).
    """

    def perform_create(self, serializer):
        data = {}
        if hasattr(serializer.Meta.model, 'company'):
            data['company'] = self.request.user.company
        data['created_by'] = self.request.user
        data['updated_by'] = self.request.user
        serializer.save(**data)

    @transaction.atomic
    def perform_update(self, serializer):
        obj = self.get_object()
        updated = serializer.save(updated_by=self.request.user)
        self.log_changes(obj, updated)

    def log_changes(self, old, new):
        """Переопределяется в наследнике"""
        pass


class ChangeLogHistoryMixin:
    """
    Миксин для GET /<id>/history/
    """
    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        instance = self.get_object()
        logs = instance.history.all()
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(logs, many=True)
        return Response(serializer.data)
