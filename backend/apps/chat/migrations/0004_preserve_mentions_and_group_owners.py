import re
from django.db import migrations
from django.db.models import F
from django.utils import timezone


def preserve_existing_data(apps, schema_editor):
    Conversation = apps.get_model('chat', 'Conversation')
    Participant = apps.get_model('chat', 'Participant')
    Message = apps.get_model('chat', 'Message')
    alias = schema_editor.connection.alias
    Conversation.objects.using(alias).filter(owner__isnull=True).update(owner_id=F('created_by_id'))
    Conversation.objects.using(alias).filter(is_deleted=True, deleted_at__isnull=True).update(deleted_at=timezone.now())
    through = Message.mentioned_users.through
    target_field = next(field for field in through._meta.fields if field.many_to_one and field.related_model != Message)
    room_id, users = None, {}
    for message in Message.objects.using(alias).order_by('conversation_id', 'id').iterator(chunk_size=200):
        if message.conversation_id != room_id:
            room_id = message.conversation_id
            users = {member.user.username.casefold(): member.user for member in Participant.objects.using(alias)
                     .filter(conversation_id=room_id).select_related('user')}
        found = []
        for match in re.finditer(r'(?<![\w@])@([\w.@+-]+)', message.text):
            nickname = match.group(1)
            user = users.get(nickname.casefold())
            if not user:
                nickname = nickname.rstrip('.')
                user = users.get(nickname.casefold())
            if user:
                start = len(message.text[:match.start()].encode('utf-16-le')) // 2
                name = f'{user.first_name} {user.last_name}'.strip() or user.username
                found.append({'id': user.pk, 'name': name, 'username': user.username, 'start': start,
                              'end': start + len(('@' + nickname).encode('utf-16-le')) // 2})
        if found:
            Message.objects.using(alias).filter(pk=message.pk).update(mention_snapshot=found)
            through.objects.using(alias).bulk_create([
                through(message_id=message.pk, **{target_field.attname: user_id})
                for user_id in {mention['id'] for mention in found}
            ], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [('chat', '0003_conversationevent_reaction_storagepolicy_and_more')]
    operations = [migrations.RunPython(preserve_existing_data, migrations.RunPython.noop)]
