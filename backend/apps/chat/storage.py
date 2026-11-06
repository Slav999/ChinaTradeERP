import uuid
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateChatStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.BASE_DIR / 'private_chat_files')

    def url(self, name):
        raise ValueError('Chat files are available only through authenticated download views.')


def attachment_path(instance, filename):
    return f'{instance.message.conversation.company_id}/{uuid.uuid4().hex}'
