from django.conf import settings
from django.db import models
from .storage import PrivateChatStorage, attachment_path


class Conversation(models.Model):
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE)
    is_group = models.BooleanField(default=False)
    title = models.CharField(max_length=120, blank=True)
    # Sorted user IDs; NULL for groups. Prevent duplicate direct conversations.
    direct_key = models.CharField(max_length=64, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_chat_groups')
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['company', 'direct_key'], name='chat_unique_direct_company')]


class Participant(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='participants', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    last_read_id = models.PositiveBigIntegerField(default=0)
    hidden_before_id = models.PositiveBigIntegerField(default=0)
    is_hidden = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_marked_unread = models.BooleanField(default=False)
    cleared_at = models.DateTimeField(null=True, blank=True)
    notification_mode = models.CharField(max_length=12, default='all', choices=[('all', 'All'), ('mentions', 'Mentions'), ('off', 'Off')])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['conversation', 'user'], name='chat_unique_participant')]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField(max_length=5000, blank=True)
    reference_type = models.CharField(max_length=24, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    client_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveBigIntegerField(default=0)
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    mention_snapshot = models.JSONField(default=list, blank=True)
    mentioned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='chat_mentions')
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['conversation', 'id'], name='chat_message_room_id'),
                   models.Index(fields=['conversation', 'revision'], name='chat_message_revision')]
        constraints = [models.UniqueConstraint(fields=['conversation', 'sender', 'client_id'], name='chat_unique_message_retry')]


class Attachment(models.Model):
    message = models.ForeignKey(Message, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(storage=PrivateChatStorage(), upload_to=attachment_path)
    name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    purged_at = models.DateTimeField(null=True, blank=True)


class Reaction(models.Model):
    message = models.ForeignKey(Message, related_name='reactions', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=8)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['message', 'user', 'emoji'], name='chat_unique_reaction')]


class ReadReceipt(models.Model):
    message = models.ForeignKey(Message, related_name='read_receipts', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['message', 'user'], name='chat_unique_read_receipt')]


class ConversationEvent(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='events', on_delete=models.CASCADE)
    text = models.CharField(max_length=1000)
    after_message_id = models.PositiveBigIntegerField(default=0)
    revision = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['conversation', 'revision'], name='chat_event_revision')]


class StoragePolicy(models.Model):
    company = models.OneToOneField('users.Company', on_delete=models.CASCADE, related_name='chat_storage_policy')
    deleted_file_retention_days = models.PositiveIntegerField(default=30)
