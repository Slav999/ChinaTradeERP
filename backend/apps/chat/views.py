from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from users.models import Company, CompanyMembership
from .models import Attachment, Conversation, Message, Participant, ReadReceipt
from .serializers import ConversationCreateSerializer, GroupUpdateSerializer, MessageCreateSerializer, MessageSerializer, employee_data
from .references import reference_queryset, search_references
from .uploads import validate_uploads
from .queries import conversation_data, hydrated_messages, integer, list_conversations, membership_rows
from .history import history_payload
from .services import owner_id, record_event, record_reads, set_mentions, touch


class CompanyChanged(APIException):
    status_code = 409
    default_detail = 'The active company changed. Reopen the chat.'


class ActiveChatCompany(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_active or not request.user.company_id or not request.user.is_email_verified:
            return False
        if request.query_params.get('company_id') != str(request.user.company_id):
            raise CompanyChanged()
        return CompanyMembership.objects.filter(
            company_id=request.user.company_id, user=request.user,
            status=CompanyMembership.STATUS_ACTIVE,
        ).exists()


class ChatReadThrottle(UserRateThrottle):
    scope = 'chat_read'
    rate = '120/minute'


class ChatWriteThrottle(UserRateThrottle):
    scope = 'chat_write'
    rate = '30/minute'


class ChatReadMarkerThrottle(UserRateThrottle):
    scope = 'chat_read_marker'
    rate = '60/minute'


class ChatView(APIView):
    permission_classes = [IsAuthenticated, ActiveChatCompany]

    def get_throttles(self):
        # Polling has its own budget and does not consume the ERP's daily limit.
        if self.request.path.endswith('/read/'):
            return [ChatReadMarkerThrottle()]
        return [ChatReadThrottle() if self.request.method == 'GET' else ChatWriteThrottle()]

    def room(self, pk, lock=False):
        rooms = Conversation.objects.filter(company_id=self.request.user.company_id, is_deleted=False)
        if lock:
            rooms = rooms.select_for_update()
        room = get_object_or_404(rooms, pk=pk)
        get_object_or_404(Participant, conversation=room, user=self.request.user)
        return room

    def visible_messages(self, room):
        member = get_object_or_404(Participant, conversation=room, user=self.request.user)
        return room.messages.filter(pk__gt=member.hidden_before_id)

    def serialize_message(self, message):
        member = message.conversation.participants.get(user=self.request.user)
        return MessageSerializer(message, context={'request': self.request, 'history_after_id': member.hidden_before_id}).data


def active_users(company_id):
    return get_user_model().objects.filter(
        is_active=True,
        company_memberships__company_id=company_id,
        company_memberships__status=CompanyMembership.STATUS_ACTIVE,
    )


class EmployeesView(ChatView):
    def get(self, request):
        users = active_users(request.user.company_id).exclude(pk=request.user.pk).order_by('first_name', 'username')
        exclude_room = integer(request.query_params, 'exclude_conversation', minimum=1)
        if exclude_room:
            room = self.room(exclude_room)
            users = users.exclude(pk__in=room.participants.values('user_id'))
        search = request.query_params.get('q', '').strip()[:100]
        if search:
            users = users.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(username__icontains=search))
        limit = integer(request.query_params, 'limit', default=20, minimum=1, maximum=50)
        return Response([employee_data(user) for user in users[:limit]])


class ConversationsView(ChatView):
    def get(self, request):
        return Response(list_conversations(request))

    @transaction.atomic
    def post(self, request):
        data = ConversationCreateSerializer(data=request.data, context={'request': request})
        data.is_valid(raise_exception=True)
        values = data.validated_data
        ids = values['user_ids'] | {request.user.pk}
        if set(active_users(request.user.company_id).filter(pk__in=ids).values_list('pk', flat=True)) != ids:
            raise serializers.ValidationError('Select active employees of this company only.')
        if values['is_group']:
            room = Conversation.objects.create(company_id=request.user.company_id, is_group=True,
                                               title=values['title'], created_by=request.user, owner=request.user)
            created = True
        else:
            room, created = Conversation.objects.get_or_create(
                company_id=request.user.company_id, direct_key=':'.join(map(str, sorted(ids))),
                defaults={'created_by': request.user},
            )
        if created:
            Participant.objects.bulk_create([Participant(conversation=room, user_id=pk) for pk in ids])
            if room.is_group:
                record_event(room, f'{employee_data(request.user)["name"]} создал(а) группу «{room.title}».')
        else:
            Participant.objects.filter(conversation=room, user=request.user).update(is_hidden=False)
        return Response({'id': room.pk}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessagesView(ChatView):
    def get(self, request, pk):
        return Response(history_payload(request, self.room(pk)))

    @transaction.atomic
    def post(self, request, pk):
        room = self.room(pk, lock=True)
        client_id = serializers.UUIDField().run_validation(request.data.get('client_id'))
        existing = hydrated_messages(room.messages).filter(sender=request.user, client_id=client_id).first()
        if existing:
            return Response(self.serialize_message(existing))
        files = validate_uploads(request.FILES.getlist('files'))
        data = MessageCreateSerializer(data=request.data, context={'has_files': bool(files)})
        data.is_valid(raise_exception=True)
        values = data.validated_data
        if values['reference_type']:
            get_object_or_404(reference_queryset(request.user, values['reference_type']), pk=values['reference_id'])
        if values.get('reply_to_id'):
            get_object_or_404(self.visible_messages(room), pk=values['reply_to_id'], deleted_at__isnull=True)
        if files:
            # Coordinate immutable uploads with private backup/purge operations.
            Company.objects.select_for_update().get(pk=room.company_id)
        message = Message.objects.create(
            conversation=room, sender=request.user, client_id=client_id, text=values['text'],
            reference_type=values['reference_type'], reference_id=values.get('reference_id'), reply_to_id=values.get('reply_to_id'),
        )
        saved_files = []
        try:
            for file, name, mime in files:
                attachment = Attachment(message=message, name=name, size=file.size, content_type=mime)
                attachment.file.save(name, file, save=False)
                saved_files.append(attachment.file)
                attachment.save()
            message.revision = touch(room, activity=True)
            set_mentions(message)
            message.save(update_fields=['revision', 'mention_snapshot'])
            room.participants.filter(user=request.user, is_archived=True).update(is_archived=False)
            result = self.serialize_message(message)
        except Exception:
            for file in saved_files:
                file.delete(save=False)
            raise
        return Response(result, status=201)


class ReadView(ChatView):
    @transaction.atomic
    def post(self, request, pk):
        room = self.room(pk, lock=True)
        if 'message_ids' in request.data:
            ids = set(serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100)
                      .run_validation(request.data['message_ids']))
            member = room.participants.get(user=request.user)
            if not ids:
                member.is_marked_unread = False
                member.save(update_fields=['is_marked_unread'])
                return Response({'last_read_id': member.last_read_id, 'read_message_ids': []})
            visible = self.visible_messages(room)
            if set(visible.filter(pk__in=ids).values_list('pk', flat=True)) != ids:
                from rest_framework.exceptions import NotFound
                raise NotFound('Сообщения недоступны.')
            record_reads(request.user, visible.filter(pk__in=ids))
            first_missing = visible.filter(pk__gt=member.last_read_id, deleted_at__isnull=True).exclude(sender=request.user)
            first_missing = first_missing.exclude(read_receipts__user=request.user).order_by('id').values_list('id', flat=True).first()
            through = visible if not first_missing else visible.filter(pk__lt=first_missing)
            boundary = through.order_by('-id').values_list('id', flat=True).first() or member.last_read_id
            member.last_read_id = max(member.last_read_id, boundary)
            member.is_marked_unread = False
            member.save(update_fields=['last_read_id', 'is_marked_unread'])
            return Response({'last_read_id': member.last_read_id, 'read_message_ids': sorted(ids)})
        last_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('message_id'))
        get_object_or_404(self.visible_messages(room), pk=last_id)
        Participant.objects.filter(conversation=room, user=request.user).update(
            last_read_id=Greatest(F('last_read_id'), last_id),
            is_marked_unread=False,
        )
        record_reads(request.user, self.visible_messages(room).filter(pk=last_id))
        return Response(status=204)


class ConversationDetailView(ChatView):
    def get(self, request, pk):
        self.room(pk)
        member = membership_rows(request.user).prefetch_related('conversation__participants__user').get(conversation_id=pk)
        return Response(conversation_data(member, request.user))

    @transaction.atomic
    def patch(self, request, pk):
        room = self.room(pk, lock=True)
        if not room.is_group or owner_id(room) != request.user.pk:
            raise PermissionDenied('Только создатель группы может менять её состав и название.')
        data = GroupUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        actor = employee_data(request.user)['name']
        if 'title' in values and values['title'] != room.title:
            room.title = values['title']
            room.save(update_fields=['title'])
            record_event(room, f'{actor} изменил(а) название группы на «{room.title}».')
        if 'user_ids' in values:
            ids = set(values['user_ids'])
            if request.user.pk not in ids:
                raise serializers.ValidationError('Нельзя удалить создателя группы.')
            existing = set(room.participants.values_list('user_id', flat=True))
            added = ids - existing
            removed = existing - ids
            if set(active_users(room.company_id).filter(pk__in=added).values_list('pk', flat=True)) != added:
                raise serializers.ValidationError('Добавлять можно только активных сотрудников этой компании.')
            last = room.messages.order_by('-id').values_list('id', flat=True).first() or 0
            removed_names = [employee_data(p.user)['name'] for p in room.participants.select_related('user').filter(user_id__in=removed)]
            room.participants.exclude(user_id__in=ids).delete()
            # Added and re-added colleagues can read the complete shared history.
            # Existing members' personal clearing cursors remain unchanged.
            Participant.objects.bulk_create([Participant(conversation=room, user_id=uid, last_read_id=last) for uid in added])
            added_names = [employee_data(user)['name'] for user in active_users(room.company_id).filter(pk__in=added)]
            for name in removed_names:
                record_event(room, f'{actor} удалил(а) {name} из группы.')
            for name in added_names:
                record_event(room, f'{actor} добавил(а) {name} в группу.')
        return Response(status=204)

    @transaction.atomic
    def delete(self, request, pk):
        room = self.room(pk, lock=True)
        if room.is_group:
            if owner_id(room) != request.user.pk:
                raise PermissionDenied('Только создатель может удалить группу.')
            room.is_deleted = True
            room.deleted_at = timezone.now()
            room.save(update_fields=['is_deleted', 'deleted_at'])
        else:
            self.clear(room, hide=True)
        return Response(status=204)

    def clear(self, room, hide=False):
        last = room.messages.order_by('-id').values_list('id', flat=True).first() or 0
        room.participants.filter(user=self.request.user).update(hidden_before_id=last, last_read_id=last, is_hidden=hide,
                                                             is_marked_unread=False, cleared_at=timezone.now())


class ClearView(ConversationDetailView):
    http_method_names = ['post', 'options']
    @transaction.atomic
    def post(self, request, pk):
        self.clear(self.room(pk, lock=True))
        return Response(status=204)


class AttachmentView(ChatView):
    def get(self, request, pk, attachment_id):
        room = self.room(pk)
        attachment = get_object_or_404(Attachment.objects.filter(message__in=self.visible_messages(room),
                                                                message__deleted_at__isnull=True, purged_at__isnull=True), pk=attachment_id)
        preview = request.query_params.get('preview') == '1' and attachment.content_type.startswith('image/')
        try:
            source = attachment.file.open('rb')
        except FileNotFoundError:
            from rest_framework.exceptions import NotFound
            raise NotFound('Файл недоступен.')
        response = FileResponse(source, as_attachment=not preview,
                                filename=attachment.name, content_type=attachment.content_type)
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Security-Policy'] = "default-src 'none'; sandbox"
        return response


class ReferencesView(ChatView):
    def get(self, request):
        kind = request.query_params.get('type', 'customer_order')
        return Response(search_references(request.user, kind, request.query_params.get('search', '').strip()[:100]))
