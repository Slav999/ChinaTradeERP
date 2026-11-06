from rest_framework import viewsets
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from users.access import user_has_permission


SENSITIVE_HISTORY_FIELDS = {
    'products.product': {
        'pricing.purchase.view': {'purchase_price'},
        'pricing.cost.view': {'cost_price'},
        'company.settings.manage': {'applied_markup_pct', 'applied_markup_source'},
        'pricing.sale.view': {
            'sale_price', 'automatic_sale_price', 'sale_price_mode',
        },
    },
    'supplier_orders.supplierorder': {
        'pricing.purchase.view': {
            'amount_cny', 'cny_to_local_rate', 'company_currency_code',
            'company_currency_symbol', 'item_unit_price_cny', 'unit_price_cny',
        },
    },
    'customer_orders.customerorder': {
        'pricing.sale.view': {
            'discount_pct', 'item_unit_sale_price', 'unit_sale_price',
            'total_amount', 'amount_company_currency',
        },
    },
}


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
        logs = instance.history.all().order_by('-changed_at', '-id')
        restricted_fields = set()
        for permission, field_names in SENSITIVE_HISTORY_FIELDS.get(
            instance._meta.label_lower,
            {},
        ).items():
            if not user_has_permission(request.user, permission):
                restricted_fields.update(field_names)
        if restricted_fields:
            logs = logs.exclude(field_name__in=restricted_fields)
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            logs,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)
