from django.shortcuts import get_object_or_404
from .queries import hydrated_messages, integer
from .references import message_search_condition, reference_queryset
from .serializers import EventSerializer, MessageSerializer


def history_payload(request, room):
    member = room.participants.get(user=request.user)
    visible = room.messages.filter(id__gt=member.hidden_before_id)
    live = visible.filter(deleted_at__isnull=True)
    unread = live.filter(id__gt=member.last_read_id).exclude(sender=request.user).exclude(read_receipts__user=request.user)
    first_unread = unread.order_by('id').values_list('id', flat=True).first()
    first_mention = unread.filter(mentioned_users=request.user).order_by('id').values_list('id', flat=True).first()
    context = {'request': request, 'history_after_id': member.hidden_before_id}
    if 'client_id' in request.query_params:
        from rest_framework import serializers
        client_id = serializers.UUIDField().run_validation(request.query_params['client_id'])
        matches = hydrated_messages(visible.filter(sender=request.user, client_id=client_id))
        return {'results': MessageSerializer(matches, many=True, context=context).data}
    base = {'last_read_id': member.last_read_id, 'first_unread_id': first_unread, 'first_mention_id': first_mention}
    events = room.events.all()
    if member.cleared_at:
        events = events.filter(created_at__gt=member.cleared_at)
    elif member.hidden_before_id:
        events = events.filter(after_message_id__gt=member.hidden_before_id)
    since = integer(request.query_params, 'since_revision')
    if since is not None:
        changes = list(hydrated_messages(visible.filter(revision__gt=since, revision__lte=room.revision))
                       .order_by('revision', 'id')[:101])
        event_changes = list(events.filter(revision__gt=since, revision__lte=room.revision).order_by('revision')[:101])
        cutoffs = [room.revision]
        if len(changes) > 100:
            cutoffs.append(changes[99].revision)
        if len(event_changes) > 100:
            cutoffs.append(event_changes[99].revision)
        cursor = min(cutoffs)
        return {**base, 'results': MessageSerializer([m for m in changes[:100] if m.revision <= cursor], many=True, context=context).data,
                'events': EventSerializer([e for e in event_changes[:100] if e.revision <= cursor], many=True).data,
                'sync_revision': cursor, 'has_more': cursor < room.revision}

    search = request.query_params.get('q', '').strip()[:100]
    tab = request.query_params.get('tab', '')
    if tab == 'events':
        before = integer(request.query_params, 'before', minimum=1)
        if before:
            events = events.filter(pk__lt=before)
        if search:
            events = events.filter(text__icontains=search)
        page = list(events.order_by('-id')[:21])
        return {**base, 'results': [], 'events': EventSerializer(page[:20], many=True).data, 'has_more': len(page) > 20}
    messages = visible
    if tab or search:
        messages = live
    if tab == 'files':
        messages = messages.filter(attachments__isnull=False, attachments__purged_at__isnull=True)
    elif tab == 'references':
        messages = messages.exclude(reference_type='')
    elif tab == 'pins':
        messages = messages.filter(is_pinned=True)
    if search:
        messages = messages.filter(message_search_condition(request.user, search))
    messages = messages.distinct()
    around = integer(request.query_params, 'around', minimum=1)
    if 'reference_type' in request.query_params:
        kind = request.query_params['reference_type']
        record_id = integer(request.query_params, 'reference_id', minimum=1)
        get_object_or_404(reference_queryset(request.user, kind), pk=record_id)
        target = live.filter(reference_type=kind, reference_id=record_id).order_by('-id').first()
        if target is None:
            from rest_framework.exceptions import NotFound
            raise NotFound('Обсуждение этого объекта больше недоступно.')
        around = target.pk
    elif request.query_params.get('initial') == '1':
        around = first_unread
    if 'reference_type' not in request.query_params and request.query_params.get('unread_mention') == '1':
        around = first_mention or first_unread
    before = integer(request.query_params, 'before', minimum=1)
    after = integer(request.query_params, 'after')
    limit = 20 if search or tab else 50
    if around:
        get_object_or_404(visible, pk=around)
        older = list(hydrated_messages(messages.filter(pk__lt=around)).order_by('-id')[:20])
        newer = list(hydrated_messages(messages.filter(pk__gte=around)).order_by('id')[:30])
        batch = list(reversed(older)) + newer
        has_more = False
    else:
        page = messages
        if before:
            page = page.filter(pk__lt=before)
        if after is not None:
            page = page.filter(pk__gt=after)
        batch = list(hydrated_messages(page).order_by('id' if after is not None else '-id')[:limit + 1])
        has_more = len(batch) > limit
        batch = batch[:limit]
        if after is None:
            batch.reverse()
    first, last = (batch[0].pk, batch[-1].pk) if batch else (None, None)
    has_older = messages.filter(pk__lt=first).exists() if first else False
    has_newer = messages.filter(pk__gt=last).exists() if last else False
    displayed_events = events.none()
    if not tab and not search:
        displayed_events = events.filter(after_message_id__lte=last or 0)
        if has_older and first:
            displayed_events = displayed_events.filter(after_message_id__gte=first)
    pins = hydrated_messages(live.filter(is_pinned=True)).order_by('-id')[:10]
    return {**base, 'results': MessageSerializer(batch, many=True, context=context).data,
            'read_message_ids': list(visible.filter(pk__in=[m.pk for m in batch], read_receipts__user=request.user).values_list('pk', flat=True)),
            'events': EventSerializer(displayed_events.order_by('-id')[:100], many=True).data,
            'pinned_messages': MessageSerializer(pins, many=True, context=context).data,
            'has_more': has_more, 'has_older': has_older, 'has_newer': has_newer,
            'sync_revision': room.revision, 'focus_id': around}
