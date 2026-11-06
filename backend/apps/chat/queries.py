from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from .models import Message, Participant
from .references import message_search_condition, reference_queryset
from .serializers import employee_data
from .services import active_member, owner_id


def integer(params, name, default=None, minimum=0, maximum=None):
    if name not in params:
        return default
    return serializers.IntegerField(min_value=minimum, max_value=maximum).run_validation(params[name])


def hydrated_messages(queryset):
    return queryset.select_related('sender', 'reply_to__sender').prefetch_related('attachments', 'reactions')


def membership_rows(user):
    messages = Message.objects.filter(conversation_id=OuterRef('conversation_id'), id__gt=OuterRef('hidden_before_id'))
    live = messages.filter(deleted_at__isnull=True)
    unread = live.filter(id__gt=OuterRef('last_read_id')).exclude(sender=user).exclude(read_receipts__user=user).order_by().values('conversation_id').annotate(n=Count('pk'))
    mentions = live.filter(id__gt=OuterRef('last_read_id'), mentioned_users=user).exclude(sender=user).exclude(read_receipts__user=user).order_by().values('conversation_id').annotate(n=Count('pk'))
    return Participant.objects.filter(user=user, conversation__company_id=user.company_id,
                                      conversation__is_deleted=False).select_related('conversation').annotate(
        unread=Subquery(unread.values('n')[:1]), unread_mentions=Subquery(mentions.values('n')[:1]),
        last_id=Subquery(messages.order_by('-id').values('id')[:1]),
        last_text=Subquery(messages.order_by('-id').values('text')[:1]),
        last_deleted=Subquery(messages.order_by('-id').values('deleted_at')[:1]),
        last_time=Subquery(messages.order_by('-id').values('created_at')[:1]),
        incoming_id=Subquery(live.exclude(sender=user).order_by('-id').values('id')[:1]),
        mention_id=Subquery(live.filter(mentioned_users=user).exclude(sender=user).order_by('-id').values('id')[:1]),
    ).filter(Q(is_hidden=False) | Q(last_id__isnull=False))


def notification_row(member):
    return {'id': member.conversation_id, 'revision': member.conversation.revision,
            'unread_count': member.unread or int(member.is_marked_unread), 'unread_mention_count': member.unread_mentions or 0,
            'is_marked_unread': member.is_marked_unread,
            'last_incoming_message_id': member.incoming_id, 'last_mention_message_id': member.mention_id,
            'notification_mode': member.notification_mode}


def conversation_data(member, user, compact=False):
    row = notification_row(member)
    if compact:
        return row
    room = member.conversation
    people = [employee_data(p.user) for p in room.participants.all()]
    row.update({'title': room.title if room.is_group else next((p['name'] for p in people if p['id'] != user.pk), 'Чат'),
                'is_group': room.is_group, 'created_by_id': room.created_by_id, 'owner_id': owner_id(room),
                'participants': people, 'history_after_id': member.hidden_before_id, 'last_read_id': member.last_read_id,
                'is_archived': member.is_archived, 'last_text': 'Сообщение удалено' if member.last_deleted else (member.last_text or '')[:160],
                'last_message_deleted': bool(member.last_deleted),
                'last_time': member.last_time,
                'last_message_id': member.last_id,
                'can_take_over': room.is_group and user.is_company_admin and not active_member(room.company_id, owner_id(room))})
    return row


def related_members(request, members=None):
    user = request.user
    kind = request.query_params.get('reference_type', '')
    record_id = integer(request.query_params, 'reference_id', minimum=1)
    get_object_or_404(reference_queryset(user, kind), pk=record_id)
    if members is None:
        members = Participant.objects.filter(user=user, conversation__company_id=user.company_id,
                                             conversation__is_deleted=False)
    links = Message.objects.filter(reference_type=kind, reference_id=record_id, deleted_at__isnull=True,
                                   conversation_id=OuterRef('conversation_id'), id__gt=OuterRef('hidden_before_id'))
    return members.annotate(has_link=Exists(links)).filter(has_link=True)


def list_conversations(request, related=False):
    user = request.user
    all_members = membership_rows(user)
    notifications = [notification_row(member) for member in all_members]
    payload = {'unread_count': sum(row['unread_count'] for row in notifications), 'notifications': notifications}
    if request.query_params.get('compact') == '1':
        return {**payload, 'results': []}
    members = all_members
    if related:
        members = related_members(request, members)
    else:
        members = members.filter(is_archived=request.query_params.get('archived') == '1')
    search = request.query_params.get('q', '').strip()[:100]
    if search:
        matching_messages = Message.objects.filter(
            conversation_id=OuterRef('conversation_id'), id__gt=OuterRef('hidden_before_id'), deleted_at__isnull=True,
        ).filter(message_search_condition(user, search))
        members = members.annotate(matches_message=Exists(matching_messages)).filter(Q(conversation__title__icontains=search) |
                                 Q(conversation__participants__user__first_name__icontains=search) |
                                 Q(conversation__participants__user__last_name__icontains=search) |
                                 Q(conversation__participants__user__middle_name__icontains=search) |
                                 Q(conversation__participants__user__username__icontains=search) | Q(matches_message=True)).distinct()
    offset = integer(request.query_params, 'offset', default=0, maximum=100000)
    limit = integer(request.query_params, 'limit', default=30, minimum=1, maximum=50)
    page = list(members.order_by('-conversation__updated_at', '-conversation_id')
                .prefetch_related('conversation__participants__user')[offset:offset + limit + 1])
    payload.update({'results': [conversation_data(member, user) for member in page[:limit]], 'total_count': members.count(),
                    'has_more': len(page) > limit, 'next_offset': offset + min(limit, len(page))})
    selected_id = integer(request.query_params, 'selected_id', minimum=1)
    if selected_id:
        selected = all_members.prefetch_related('conversation__participants__user').filter(conversation_id=selected_id).first()
        payload['selected'] = conversation_data(selected, user) if selected else None
    return payload
