from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from .models import ReadReceipt
from .serializers import employee_data
from .views import ChatView


class ReadStatusView(ChatView):
    def get(self, request, pk):
        room = self.room(pk)
        raw = request.query_params.get('message_ids', '')
        ids = set(serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100)
                  .run_validation(raw.split(',') if raw else []))
        own = self.visible_messages(room).filter(pk__in=ids, sender=request.user, deleted_at__isnull=True)
        if set(own.values_list('pk', flat=True)) != ids:
            raise NotFound('Сообщения недоступны.')
        recipients = [employee_data(p.user) for p in room.participants.select_related('user').exclude(user=request.user)]
        rows = {pk: [] for pk in ids}
        receipts = ReadReceipt.objects.filter(message_id__in=ids, user_id__in=[p['id'] for p in recipients])
        for receipt in receipts.order_by('user_id').values('message_id', 'user_id', 'read_at'):
            rows[receipt['message_id']].append({'user_id': receipt['user_id'], 'read_at': receipt['read_at']})
        return Response({'recipients': recipients, 'results': [{'id': pk, 'read_by': rows[pk]} for pk in sorted(ids)]})
