from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response
from .models import Reaction
from .queries import hydrated_messages, list_conversations, related_members
from .serializers import MemberPreferencesSerializer, employee_data
from .services import REACTIONS, active_member, owner_id, record_event, refresh_reply_previews, set_mentions, storage_policy, storage_usage, touch
from .views import ChatView


class MessageChanged(APIException):
    status_code = 412
    default_detail = 'Сообщение уже изменилось. Откройте его заново; ваш текст сохранён.'


class MessageDetailView(ChatView):
    def message(self, room, message_id, live=False):
        queryset = self.visible_messages(room)
        if live:
            queryset = queryset.filter(deleted_at__isnull=True)
        return get_object_or_404(hydrated_messages(queryset), pk=message_id)

    def get(self, request, pk, message_id):
        return Response(self.serialize_message(self.message(self.room(pk), message_id)))

    @transaction.atomic
    def patch(self, request, pk, message_id):
        room = self.room(pk, lock=True)
        message = self.message(room, message_id, live=True)
        if message.sender_id != request.user.pk:
            raise PermissionDenied('Можно редактировать только свои сообщения.')
        if 'expected_revision' in request.data:
            expected = serializers.IntegerField(min_value=0).run_validation(request.data['expected_revision'])
            if expected != message.revision:
                raise MessageChanged()
        text = serializers.CharField(max_length=5000, allow_blank=True).run_validation(request.data.get('text'))
        if not text and not message.reference_type and not message.attachments.filter(purged_at__isnull=True).exists():
            raise serializers.ValidationError('Сообщение не может быть пустым.')
        if text != message.text:
            message.text = text
            message.edited_at = timezone.now()
            message.revision = touch(room)
            set_mentions(message)
            message.save(update_fields=['text', 'edited_at', 'revision', 'mention_snapshot'])
            refresh_reply_previews(message, room)
        return Response(self.serialize_message(message))

    @transaction.atomic
    def delete(self, request, pk, message_id):
        room = self.room(pk, lock=True)
        message = self.message(room, message_id)
        if message.sender_id != request.user.pk:
            raise PermissionDenied('Можно удалять только свои сообщения.')
        if not message.deleted_at:
            message.text = ''; message.reference_type = ''; message.reference_id = None
            message.deleted_at = timezone.now(); message.is_pinned = False
            message.mention_snapshot = []; message.reply_to = None
            message.revision = touch(room)
            message.save(update_fields=['text', 'reference_type', 'reference_id', 'deleted_at', 'is_pinned',
                                        'mention_snapshot', 'reply_to', 'revision'])
            message.mentioned_users.clear(); message.reactions.all().delete()
            refresh_reply_previews(message, room)
        return Response(self.serialize_message(message))


class ReactionView(MessageDetailView):
    http_method_names = ['post', 'options']
    @transaction.atomic
    def post(self, request, pk, message_id):
        room = self.room(pk, lock=True)
        message = self.message(room, message_id, live=True)
        emoji = serializers.ChoiceField(choices=REACTIONS).run_validation(request.data.get('emoji'))
        active = serializers.BooleanField().run_validation(request.data.get('active', True))
        if active:
            removed, _ = Reaction.objects.filter(message=message, user=request.user).exclude(emoji=emoji).delete()
            _, created = Reaction.objects.get_or_create(message=message, user=request.user, emoji=emoji)
            changed = removed or created
        else:
            changed, _ = Reaction.objects.filter(message=message, user=request.user, emoji=emoji).delete()
        if changed:
            message.revision = touch(room)
            message.save(update_fields=['revision'])
        message._prefetched_objects_cache.pop('reactions', None)
        return Response(self.serialize_message(message))


class PinView(MessageDetailView):
    http_method_names = ['post', 'options']
    @transaction.atomic
    def post(self, request, pk, message_id):
        room = self.room(pk, lock=True)
        if room.is_group and owner_id(room) != request.user.pk:
            raise PermissionDenied('Сообщения в группе закрепляет её администратор.')
        message = self.message(room, message_id, live=True)
        pinned = serializers.BooleanField().run_validation(request.data.get('pinned'))
        if pinned != message.is_pinned:
            if pinned and room.messages.filter(is_pinned=True, deleted_at__isnull=True).count() >= 10:
                raise serializers.ValidationError('В переписке можно закрепить не более 10 сообщений.')
            message.is_pinned = pinned; message.revision = touch(room)
            message.save(update_fields=['is_pinned', 'revision'])
        return Response(self.serialize_message(message))


class PreferencesView(ChatView):
    @transaction.atomic
    def patch(self, request, pk):
        room = self.room(pk, lock=True)
        data = MemberPreferencesSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        room.participants.filter(user=request.user).update(**data.validated_data)
        return Response(status=204)


class TransferView(ChatView):
    @transaction.atomic
    def post(self, request, pk):
        room = self.room(pk, lock=True)
        can_recover = request.user.is_company_admin and not active_member(room.company_id, owner_id(room))
        if not room.is_group or (owner_id(room) != request.user.pk and not can_recover):
            raise PermissionDenied('Передать управление может администратор этой группы.')
        user_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('user_id'))
        member = get_object_or_404(room.participants.select_related('user'), user_id=user_id)
        if not active_member(room.company_id, user_id):
            raise serializers.ValidationError('Выберите активного участника компании.')
        if owner_id(room) != user_id:
            room.owner_id = user_id; room.save(update_fields=['owner'])
            record_event(room, f'{employee_data(request.user)["name"]} передал(а) управление группой {employee_data(member.user)["name"]}.')
        return Response(status=204)


class LeaveView(ChatView):
    @transaction.atomic
    def post(self, request, pk):
        room = self.room(pk, lock=True)
        if not room.is_group:
            raise serializers.ValidationError('Выйти можно только из группы.')
        if owner_id(room) == request.user.pk:
            if room.participants.count() > 1:
                raise serializers.ValidationError('Сначала передайте управление другому участнику.')
            room.is_deleted = True; room.deleted_at = timezone.now()
            room.save(update_fields=['is_deleted', 'deleted_at'])
        record_event(room, f'{employee_data(request.user)["name"]} вышел(ла) из группы.')
        room.participants.filter(user=request.user).delete()
        return Response(status=204)


class RelatedView(ChatView):
    def get(self, request):
        if request.query_params.get('exists') == '1':
            return Response({'has_discussions': related_members(request).exists()})
        return Response(list_conversations(request, related=True))


class StorageView(ChatView):
    def get(self, request):
        policy = storage_policy(request.user.company_id)
        return Response({'used_bytes': storage_usage(request.user.company_id),
                         'deleted_file_retention_days': policy.deleted_file_retention_days,
                         'can_manage': request.user.is_company_admin})

    @transaction.atomic
    def patch(self, request):
        if not request.user.is_company_admin:
            raise PermissionDenied('Хранением удалённых файлов управляет администратор компании.')
        policy = storage_policy(request.user.company_id, lock=True)
        if 'deleted_file_retention_days' in request.data:
            policy.deleted_file_retention_days = serializers.IntegerField(min_value=1, max_value=3650).run_validation(request.data['deleted_file_retention_days'])
        policy.save()
        return self.get(request)
