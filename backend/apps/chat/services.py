from django.db.models import Sum
from django.utils import timezone
from users.models import Company, CompanyMembership
from .models import Attachment, ConversationEvent, Message, ReadReceipt, StoragePolicy

REACTIONS = ['👍', '✅', '👀', '❤️', '🙏']


def record_reads(user, messages):
    ids = list(messages.filter(deleted_at__isnull=True).exclude(sender=user).values_list('pk', flat=True))
    now = timezone.now()
    ReadReceipt.objects.bulk_create(
        [ReadReceipt(message_id=pk, user=user, read_at=now) for pk in ids], ignore_conflicts=True,
    )
    # Previously retained sparse receipts have no known time; this view confirms it now.
    ReadReceipt.objects.filter(user=user, message_id__in=ids, read_at__isnull=True).update(read_at=now)


def owner_id(room):
    return room.owner_id or room.created_by_id


def touch(room, activity=False):
    # Call only with the conversation row locked inside a transaction.
    room.revision += 1
    fields = ['revision']
    if activity:
        room.updated_at = timezone.now()
        fields.append('updated_at')
    room.save(update_fields=fields)
    return room.revision


def record_event(room, text):
    return ConversationEvent.objects.create(
        conversation=room, text=text[:1000], revision=touch(room),
        after_message_id=room.messages.order_by('-id').values_list('id', flat=True).first() or 0,
    )


def set_mentions(message):
    from .serializers import text_mentions
    people = [p.user for p in message.conversation.participants.select_related('user')]
    message.mention_snapshot = text_mentions(message.text, people)
    message.mentioned_users.set({p['id'] for p in message.mention_snapshot})


def refresh_reply_previews(message, room):
    replies = list(Message.objects.filter(reply_to=message).only('id', 'revision').order_by('id'))
    for reply in replies:
        room.revision += 1
        reply.revision = room.revision
    if replies:
        Message.objects.bulk_update(replies, ['revision'], batch_size=200)
        room.save(update_fields=['revision'])


def storage_usage(company_id):
    return Attachment.objects.filter(message__conversation__company_id=company_id, purged_at__isnull=True).aggregate(total=Sum('size'))['total'] or 0


def storage_policy(company_id, lock=False):
    if lock:
        Company.objects.select_for_update().get(pk=company_id)
    return StoragePolicy.objects.get_or_create(company_id=company_id)[0]


def active_member(company_id, user_id):
    return CompanyMembership.objects.filter(company_id=company_id, user_id=user_id, status='active', user__is_active=True).exists()
