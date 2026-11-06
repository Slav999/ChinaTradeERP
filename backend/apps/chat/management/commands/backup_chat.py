import hashlib
import json
from itertools import chain
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from users.models import Company
from chat.models import Attachment


class Command(BaseCommand):
    help = 'Create a private ZIP containing chat database records, immutable uploads and SHA-256 checksums. User/company records must be backed up with the main database.'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True, help='New ZIP file path (existing files are never overwritten).')

    def handle(self, *args, **options):
        target = Path(options['output']).resolve()
        if target.exists():
            raise CommandError('The output already exists; choose a new backup filename.')
        if not target.parent.is_dir():
            raise CommandError('The output directory must already exist.')
        independent = not connection.in_atomic_block
        created = False
        try:
            with transaction.atomic():
                if independent and connection.vendor == 'postgresql':
                    with connection.cursor() as cursor:
                        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                # Uploads and purge operations take the same company lock.
                list(Company.objects.select_for_update().order_by('pk').values_list('pk', flat=True))
                records = chain.from_iterable(model.objects.order_by('pk').iterator() for model in apps.get_app_config('chat').get_models())
                metadata = serializers.serialize('json', records)
                manifest = {'version': 1, 'created_at': timezone.now().isoformat(), 'files': [],
                            'requires': 'Restore together with the matching main database backup (users and companies).'}
                with ZipFile(target, 'x', ZIP_DEFLATED) as archive:
                    created = True
                    archive.writestr('chat.json', metadata)
                    for attachment in Attachment.objects.filter(purged_at__isnull=True).order_by('pk').iterator():
                        digest = hashlib.sha256()
                        entry = f'files/{attachment.pk}'
                        with attachment.file.open('rb') as source, archive.open(entry, 'w') as destination:
                            for block in iter(lambda: source.read(1024 * 1024), b''):
                                digest.update(block); destination.write(block)
                        manifest['files'].append({'attachment_id': attachment.pk, 'storage_name': attachment.file.name,
                                                  'entry': entry, 'size': attachment.size, 'sha256': digest.hexdigest()})
                    archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        except Exception as error:
            if created:
                target.unlink(missing_ok=True)
            raise CommandError(f'Backup failed: {error}') from error
        self.stdout.write(f'Created private chat backup: {target}')
