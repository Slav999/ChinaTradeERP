import re
from rest_framework import serializers

from .models import ConversationEvent, Message
from .references import visible_reference


def employee_data(user):
    return {'id': user.pk, 'name': user.get_full_name().strip() or user.username, 'username': user.username}


def text_mentions(text, people):
    users = {person.username.casefold(): person for person in people}
    found = []
    for match in re.finditer(r'(?<![\w@])@([\w.@+-]+)', text):
        nickname = match.group(1)
        user = users.get(nickname.casefold())
        if not user:
            nickname = nickname.rstrip('.')
            user = users.get(nickname.casefold())
        if user:
            # UTF-16 offsets agree with JS slicing, including text containing emoji.
            start = len(text[:match.start()].encode('utf-16-le')) // 2
            length = len(('@' + nickname).encode('utf-16-le')) // 2
            found.append({**employee_data(user), 'start': start, 'end': start + length})
    return found


class ConversationCreateSerializer(serializers.Serializer):
    is_group = serializers.BooleanField(default=False)
    title = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=99)

    def validate(self, attrs):
        ids = set(attrs['user_ids']) - {self.context['request'].user.pk}
        if not ids or (not attrs['is_group'] and len(ids) != 1):
            raise serializers.ValidationError('Select one colleague for a direct chat, or colleagues for a group.')
        if attrs['is_group'] and not attrs['title'].strip():
            raise serializers.ValidationError({'title': 'A group name is required.'})
        attrs['user_ids'] = ids
        return attrs


class MessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000, trim_whitespace=True, allow_blank=True, default='')
    client_id = serializers.UUIDField()
    reference_type = serializers.ChoiceField(choices=['', 'customer_order', 'supplier_order', 'product', 'counterparty'], default='')
    reference_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    reply_to_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def validate(self, attrs):
        if bool(attrs['reference_type']) != bool(attrs.get('reference_id')):
            raise serializers.ValidationError('Both reference type and ID are required.')
        if not attrs['text'] and not attrs['reference_type'] and not self.context.get('has_files'):
            raise serializers.ValidationError('Добавьте сообщение, файл или ссылку на объект.')
        return attrs


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    mentions = serializers.SerializerMethodField()
    reply = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'sender_name', 'text', 'client_id', 'created_at', 'attachments', 'reference', 'mentions',
                  'reply', 'reactions', 'edited_at', 'deleted_at', 'is_pinned', 'revision']

    def to_representation(self, obj):
        if obj.deleted_at:
            return {'id': obj.pk, 'sender_id': obj.sender_id, 'sender_name': self.get_sender_name(obj),
                    'text': 'Сообщение удалено', 'client_id': str(obj.client_id), 'created_at': obj.created_at.isoformat(),
                    'edited_at': None, 'deleted_at': obj.deleted_at.isoformat(), 'is_pinned': False,
                    'revision': obj.revision, 'attachments': [], 'reference': None, 'mentions': [], 'reply': None, 'reactions': []}
        return super().to_representation(obj)

    def get_sender_name(self, obj):
        return employee_data(obj.sender)['name']

    def get_attachments(self, obj):
        return [{'id': a.pk, 'name': a.name, 'size': a.size, 'is_image': a.content_type.startswith('image/')}
                for a in obj.attachments.all() if not a.purged_at]

    def get_reference(self, obj):
        return visible_reference(self.context['request'].user, obj.reference_type, obj.reference_id) if obj.reference_type else None

    def get_mentions(self, obj):
        return obj.mention_snapshot

    def get_reply(self, obj):
        parent = obj.reply_to
        if not parent:
            return None
        if parent.conversation_id != obj.conversation_id or parent.pk <= self.context.get('history_after_id', 0):
            return {'id': None, 'text': 'Сообщение недоступно', 'sender_name': ''}
        return {'id': parent.pk, 'sender_name': self.get_sender_name(parent),
                'text': 'Сообщение удалено' if parent.deleted_at else (parent.text[:200] or 'Вложение или объект'),
                'deleted': bool(parent.deleted_at), 'is_placeholder': not bool(parent.text)}

    def get_reactions(self, obj):
        grouped = {}
        for reaction in obj.reactions.all():
            value = grouped.setdefault(reaction.emoji, {'emoji': reaction.emoji, 'count': 0, 'mine': False})
            value['count'] += 1
            value['mine'] |= reaction.user_id == self.context['request'].user.pk
        return list(grouped.values())


class GroupUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, required=False)
    user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100, required=False)


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationEvent
        fields = ['id', 'text', 'created_at', 'revision', 'after_message_id']


class MemberPreferencesSerializer(serializers.Serializer):
    notification_mode = serializers.ChoiceField(choices=['all', 'mentions', 'off'], required=False)
    is_archived = serializers.BooleanField(required=False)
    is_marked_unread = serializers.BooleanField(required=False)
