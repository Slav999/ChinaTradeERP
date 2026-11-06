from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from users.models import Company
from chat.models import Attachment
from chat.services import storage_policy


class Command(BaseCommand):
    help = 'Preview or purge files belonging to deleted chat messages/groups after their retention period. Active messages are never purged.'

    def add_arguments(self, parser):
        parser.add_argument('--company', type=int)
        parser.add_argument('--apply', action='store_true', help='Physically remove eligible files. Without this option the command is read-only.')

    def handle(self, *args, **options):
        companies = Company.objects.all()
        if options.get('company'):
            companies = companies.filter(pk=options['company'])
        count, total = 0, 0
        for company in companies.order_by('pk'):
            with transaction.atomic():
                if options['apply']:
                    policy = storage_policy(company.pk, lock=True)
                    days = policy.deleted_file_retention_days
                else:
                    days = getattr(getattr(company, 'chat_storage_policy', None), 'deleted_file_retention_days', 30)
                cutoff = timezone.now() - timedelta(days=days)
                eligible = Attachment.objects.filter(message__conversation__company=company, purged_at__isnull=True).filter(
                    Q(message__deleted_at__lt=cutoff) |
                    Q(message__conversation__is_deleted=True, message__conversation__deleted_at__lt=cutoff))
                for attachment in eligible.iterator():
                    count += 1; total += attachment.size
                    if options['apply']:
                        attachment.file.delete(save=False)
                        attachment.purged_at = timezone.now()
                        attachment.save(update_fields=['purged_at'])
        self.stdout.write(f'{"Purged" if options["apply"] else "Eligible (dry run)"}: {count} files, {total} bytes.')
