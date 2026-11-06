import hashlib
import io
import json
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APITestCase

from users.models import CompanyMembership
from .models import Attachment, Conversation, Message, Participant, ReadReceipt, StoragePolicy
from .test_features import ChatFeatureTests
from .tests import ChatTests


class CollaborationTests(APITestCase):
    setUp = ChatTests.setUp
    employee = ChatTests.employee
    url = ChatTests.url
    create_room = ChatTests.create_room
    send = ChatTests.send
    group = ChatFeatureTests.group
    update = ChatFeatureTests.update
    history = ChatFeatureTests.history
    upload = ChatFeatureTests.upload
    private_storage = ChatFeatureTests.private_storage
    product = ChatFeatureTests.product
    reference_message = ChatFeatureTests.reference_message

    def message_url(self, room, message, suffix=''):
        return self.url(f'conversations/{room}/messages/{message}/{suffix}')

    def reply(self, room, parent, text='Reply'):
        return self.client.post(self.url(f'conversations/{room}/messages/'),
                                {'text': text, 'reply_to_id': parent, 'client_id': str(uuid.uuid4())}, format='json')

    def test_only_author_can_edit_or_delete_and_deleted_content_is_redacted(self):
        room = self.group()
        sent = self.send(room, 'Wrong content').data
        self.client.force_authenticate(self.bob)
        self.bob.is_company_admin = True; self.bob.save()
        self.assertEqual(self.client.patch(self.message_url(room, sent['id']), {'text': 'Hijack'}).status_code, 403)
        self.assertEqual(self.client.delete(self.message_url(room, sent['id'])).status_code, 403)
        self.client.force_authenticate(self.alice)
        edited = self.client.patch(self.message_url(room, sent['id']), {'text': 'Corrected', 'expected_revision': sent['revision']})
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertIsNotNone(edited.data['edited_at'])
        stale = self.client.patch(self.message_url(room, sent['id']), {'text': 'Stale', 'expected_revision': sent['revision']})
        self.assertEqual(stale.status_code, 412)
        deleted = self.client.delete(self.message_url(room, sent['id']))
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.data['text'], 'Сообщение удалено')
        self.assertIsNotNone(deleted.data['deleted_at'])
        self.assertEqual(Message.objects.get(pk=sent['id']).text, '')
        self.assertEqual(self.client.delete(self.message_url(room, sent['id'])).status_code, 200)
        self.assertEqual(self.client.patch(self.message_url(room, sent['id']), {'text': 'Restore'}).status_code, 404)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.history(room).data['results'][0]['text'], 'Сообщение удалено')

    def test_delete_blocks_attachments_reference_mentions_reactions_and_pins(self):
        self.private_storage()
        room = self.group()
        uploaded = self.upload(room, [SimpleUploadedFile('private.txt', b'confidential')]).data
        self.client.patch(self.message_url(room, uploaded['id']), {'text': '@bob'})
        self.client.post(self.message_url(room, uploaded['id'], 'reaction/'), {'emoji': '👍', 'active': True})
        self.client.post(self.message_url(room, uploaded['id'], 'pin/'), {'pinned': True})
        self.client.delete(self.message_url(room, uploaded['id']))
        self.client.force_authenticate(self.bob)
        data = self.history(room).data['results'][0]
        for field in ['attachments', 'mentions', 'reactions']:
            self.assertEqual(data[field], [])
        self.assertFalse(data['is_pinned'])
        path = self.url(f'conversations/{room}/attachments/{uploaded["attachments"][0]["id"]}/')
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get(self.url()).data['results'][0]['unread_count'], 0)

    def test_reply_is_room_scoped_and_quotes_follow_edits_and_deletion(self):
        room = self.create_room().data['id']
        other = self.create_room([self.carol.pk]).data['id']
        parent = self.send(room, 'Original').data
        self.assertEqual(self.reply(other, parent['id']).status_code, 404)
        reply = self.reply(room, parent['id']).data
        before = Conversation.objects.get(pk=room).revision
        self.assertEqual(reply['reply']['text'], 'Original')
        self.client.patch(self.message_url(room, parent['id']), {'text': 'Changed'})
        delta = self.client.get(self.url(f'conversations/{room}/messages/') + f'&since_revision={before}').data
        self.assertEqual({message['id'] for message in delta['results']}, {parent['id'], reply['id']})
        self.assertEqual(next(message for message in delta['results'] if message['id'] == reply['id'])['reply']['text'], 'Changed')
        self.client.delete(self.message_url(room, parent['id']))
        self.assertEqual(self.history(room).data['results'][1]['reply']['text'], 'Сообщение удалено')

    def test_delta_pagination_does_not_skip_many_changed_reply_previews(self):
        room = self.create_room().data['id']
        parent = self.send(room, 'Old quote').data
        Message.objects.bulk_create([Message(conversation_id=room, sender=self.bob, text='Reply', reply_to_id=parent['id'], client_id=uuid.uuid4()) for _ in range(130)])
        cursor = Conversation.objects.get(pk=room).revision
        self.client.patch(self.message_url(room, parent['id']), {'text': 'New quote'})
        seen = set()
        for _ in range(3):
            data = self.client.get(self.url(f'conversations/{room}/messages/') + f'&since_revision={cursor}').data
            seen.update(message['id'] for message in data['results'])
            cursor = data['sync_revision']
            if not data['has_more']:
                break
        self.assertEqual(len(seen), 131)

    def test_initial_window_opens_at_first_unread_not_at_latest_fifty(self):
        room = self.create_room().data['id']
        Message.objects.bulk_create([Message(conversation_id=room, sender=self.bob, text=str(index), client_id=uuid.uuid4()) for index in range(100)])
        ids = list(Message.objects.filter(conversation_id=room).values_list('id', flat=True))
        Participant.objects.filter(conversation_id=room, user=self.alice).update(last_read_id=ids[58])
        data = self.client.get(self.url(f'conversations/{room}/messages/') + '&initial=1').data
        self.assertEqual(data['focus_id'], ids[59])
        self.assertIn(ids[59], [message['id'] for message in data['results']])
        self.assertNotIn(ids[-1], [message['id'] for message in data['results']])
        self.assertTrue(data['has_newer'])

    def test_reading_a_late_mention_does_not_mark_earlier_unseen_messages_read(self):
        room = self.create_room().data['id']
        self.client.force_authenticate(self.bob)
        first = self.send(room, 'Earlier unread').data['id']
        last = self.send(room, '@alice, look here').data['id']
        self.client.force_authenticate(self.alice)
        response = self.client.post(self.url(f'conversations/{room}/read/'), {'message_ids': [last]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertLess(response.data['last_read_id'], first)
        listed = self.client.get(self.url()).data['results'][0]
        self.assertEqual(listed['unread_count'], 1)
        self.assertEqual(listed['unread_mention_count'], 0)
        self.client.post(self.url(f'conversations/{room}/read/'), {'message_ids': [first]}, format='json')
        self.assertEqual(self.client.get(self.url()).data['unread_count'], 0)

    def test_reactions_are_idempotent_and_pinning_is_owner_only(self):
        room = self.group()
        message = self.send(room).data['id']
        self.client.force_authenticate(self.bob)
        for _ in range(2):
            response = self.client.post(self.message_url(room, message, 'reaction/'), {'emoji': '✅', 'active': True})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['reactions'], [{'emoji': '✅', 'count': 1, 'mine': True}])
        response = self.client.post(self.message_url(room, message, 'reaction/'), {'emoji': '👍', 'active': True})
        self.assertEqual(response.data['reactions'], [{'emoji': '👍', 'count': 1, 'mine': True}])
        # A delayed removal of the old emoji must not remove its replacement.
        response = self.client.post(self.message_url(room, message, 'reaction/'), {'emoji': '✅', 'active': False})
        self.assertEqual(response.data['reactions'], [{'emoji': '👍', 'count': 1, 'mine': True}])
        self.assertEqual(self.client.post(self.message_url(room, message, 'pin/'), {'pinned': True}).status_code, 403)
        response = self.client.post(self.message_url(room, message, 'reaction/'), {'emoji': '👍', 'active': False})
        self.assertEqual(response.data['reactions'], [])
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.post(self.message_url(room, message, 'pin/'), {'pinned': True}).status_code, 200)
        self.assertEqual(len(self.client.get(self.url(f'conversations/{room}/messages/') + '&tab=pins').data['results']), 1)

    def test_profile_logo_belongs_to_current_company(self):
        self.company.logo = 'company_logos/ours.png'
        self.company.save(update_fields=['logo'])
        self.other_company.logo = 'company_logos/theirs.png'
        self.other_company.save(update_fields=['logo'])
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['company_logo_url'].endswith('/company_logos/ours.png'))
        self.client.force_authenticate(self.outsider)
        response = self.client.get('/api/auth/me/')
        self.assertTrue(response.data['company_logo_url'].endswith('/company_logos/theirs.png'))

    def test_search_and_libraries_respect_personal_clearing(self):
        self.private_storage()
        room = self.group()
        self.send(room, 'Invoice discussion')
        self.upload(room, [SimpleUploadedFile('invoice.txt', b'document')])
        self.assertEqual(len(self.client.get(self.url(f'conversations/{room}/messages/') + '&q=invoice').data['results']), 2)
        self.assertEqual(len(self.client.get(self.url(f'conversations/{room}/messages/') + '&tab=files').data['results']), 1)
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.assertEqual(self.client.get(self.url(f'conversations/{room}/messages/') + '&q=invoice').data['results'], [])

    def test_owner_transfer_leave_and_event_history(self):
        room = self.group()
        response = self.client.post(self.url(f'conversations/{room}/leave/'))
        self.assertEqual(response.status_code, 400)
        response = self.client.post(self.url(f'conversations/{room}/transfer/'), {'user_id': self.bob.pk})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.update(room, title='Not owner').status_code, 403)
        self.assertEqual(self.client.post(self.url(f'conversations/{room}/leave/')).status_code, 204)
        self.assertEqual(self.history(room).status_code, 404)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.update(room, title='Owned by Bob').status_code, 204)
        events = self.client.get(self.url(f'conversations/{room}/messages/') + '&tab=events').data['events']
        self.assertTrue(any('управление' in event['text'] for event in events))
        self.assertTrue(any('вышел' in event['text'] for event in events))

    def test_only_existing_company_admin_member_can_recover_disabled_owner(self):
        room = self.group()
        CompanyMembership.objects.filter(user=self.alice, company=self.company).update(status='disabled')
        self.bob.is_company_admin = True; self.bob.save()
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(self.url(f'conversations/{room}/')).data['can_take_over'], True)
        self.assertEqual(self.client.post(self.url(f'conversations/{room}/transfer/'), {'user_id': self.bob.pk}).status_code, 204)
        self.carol.is_company_admin = True; self.carol.save()
        self.client.force_authenticate(self.carol)
        self.assertEqual(self.client.post(self.url(f'conversations/{room}/transfer/'), {'user_id': self.carol.pk}).status_code, 404)

    def test_mentions_are_stable_after_rename_and_removal(self):
        room = self.group()
        sent = self.send(room, '@bob, check').data
        self.update(room, user_ids=[self.alice.pk])
        self.bob.username = 'new-bob'; self.bob.save()
        self.assertEqual(self.history(room).data['results'][0]['mentions'], sent['mentions'])

    def test_preferences_and_archive_are_personal(self):
        room = self.group()
        response = self.client.patch(self.url(f'conversations/{room}/preferences/'), {'notification_mode': 'mentions', 'is_archived': True}, format='json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(self.url()).data['results'], [])
        archived = self.client.get(self.url() + '&archived=1').data['results'][0]
        self.assertEqual(archived['notification_mode'], 'mentions')
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(self.url()).data['results'][0]['notification_mode'], 'all')

    def read_status(self, room, ids, company=None):
        return self.client.get(self.url(f'conversations/{room}/read-status/', company) + '&message_ids=' + ','.join(map(str, ids)))

    def test_read_status_requires_actual_view_and_preserves_first_time(self):
        room = self.create_room().data['id']
        message = self.send(room).data['id']
        # Legacy cursors, personal clears and joining history are not proof of a view.
        Participant.objects.filter(conversation_id=room, user=self.bob).update(last_read_id=message)
        self.assertEqual(self.read_status(room, [message]).data['results'][0]['read_by'], [])
        self.client.force_authenticate(self.bob)
        self.client.post(self.url(f'conversations/{room}/read/'), {'message_ids': [message]}, format='json')
        receipt = ReadReceipt.objects.get(message_id=message, user=self.bob)
        self.assertIsNotNone(receipt.read_at)
        first_time = receipt.read_at
        self.client.post(self.url(f'conversations/{room}/read/'), {'message_ids': [message]}, format='json')
        receipt.refresh_from_db()
        self.assertEqual(receipt.read_at, first_time)
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.client.patch(self.url(f'conversations/{room}/preferences/'), {'is_marked_unread': True}, format='json')
        self.client.force_authenticate(self.alice)
        data = self.read_status(room, [message]).data
        self.assertEqual([p['id'] for p in data['recipients']], [self.bob.pk])
        self.assertEqual(data['results'][0]['read_by'][0]['user_id'], self.bob.pk)
        self.assertIsNotNone(data['results'][0]['read_by'][0]['read_at'])

    def test_late_view_does_not_mark_earlier_messages_read_for_author(self):
        room = self.group()
        first = self.send(room, 'Earlier').data['id']
        last = self.send(room, '@bob, look here').data['id']
        self.client.force_authenticate(self.bob)
        self.client.post(self.url(f'conversations/{room}/read/'), {'message_ids': [last]}, format='json')
        self.client.force_authenticate(self.alice)
        rows = self.read_status(room, [first, last]).data['results']
        self.assertEqual(rows[0]['read_by'], [])
        self.assertEqual(rows[1]['read_by'][0]['user_id'], self.bob.pk)
        self.update(room, user_ids=[self.alice.pk, self.bob.pk, self.carol.pk])
        self.assertNotIn(self.carol.pk, [r['user_id'] for r in self.read_status(room, [last]).data['results'][0]['read_by']])
        self.update(room, user_ids=[self.alice.pk, self.carol.pk])
        data = self.read_status(room, [last]).data
        self.assertEqual([p['id'] for p in data['recipients']], [self.carol.pk])
        self.assertEqual(data['results'][0]['read_by'], [])

    def test_read_status_is_author_only_company_scoped_and_bounded(self):
        room = self.create_room().data['id']
        message = self.send(room).data['id']
        self.assertEqual(self.read_status(room, list(range(1, 102))).status_code, 400)
        self.assertEqual(self.read_status(room, ['bad']).status_code, 400)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.read_status(room, [message]).status_code, 404)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.read_status(room, [message], self.other_company).status_code, 404)
        self.client.force_authenticate(self.carol)
        self.carol.is_company_admin = True; self.carol.save(update_fields=['is_company_admin'])
        self.assertEqual(self.read_status(room, [message]).status_code, 404)
        self.client.force_authenticate(self.alice)
        self.client.delete(self.message_url(room, message))
        self.assertEqual(self.read_status(room, [message]).status_code, 404)

    def test_legacy_read_only_records_time_for_the_explicit_message(self):
        room = self.create_room().data['id']
        first = self.send(room, 'First').data['id']
        last = self.send(room, 'Last').data['id']
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.post(self.url(f'conversations/{room}/read/'), {'message_id': last}).status_code, 204)
        self.assertFalse(ReadReceipt.objects.filter(message_id=first, user=self.bob).exists())
        self.assertTrue(ReadReceipt.objects.filter(message_id=last, user=self.bob, read_at__isnull=False).exists())

    def test_sending_restores_only_the_senders_archived_chat(self):
        for options in [{}, {'is_group': True, 'title': 'Archived team'}]:
            room = self.create_room(**options).data['id']
            prefs = self.url(f'conversations/{room}/preferences/')
            for user in [self.alice, self.bob]:
                self.client.force_authenticate(user)
                self.client.patch(prefs, {'is_archived': True}, format='json')
            self.client.force_authenticate(self.alice)
            response = self.send(room, 'Continue discussion')
            self.assertEqual(response.status_code, 201)
            self.assertFalse(Participant.objects.get(conversation_id=room, user=self.alice).is_archived)
            self.assertTrue(Participant.objects.get(conversation_id=room, user=self.bob).is_archived)
            self.assertIn(room, [row['id'] for row in self.client.get(self.url()).data['results']])
            # A delayed retry must not undo a subsequent, intentional archive.
            self.client.patch(prefs, {'is_archived': True}, format='json')
            self.assertEqual(self.send(room, 'Continue discussion', response.data['client_id']).status_code, 200)
            self.assertTrue(Participant.objects.get(conversation_id=room, user=self.alice).is_archived)

    def test_failed_send_keeps_the_chat_archived(self):
        room = self.group()
        self.client.patch(self.url(f'conversations/{room}/preferences/'), {'is_archived': True}, format='json')
        self.assertEqual(self.send(room, '').status_code, 400)
        self.assertTrue(Participant.objects.get(conversation_id=room, user=self.alice).is_archived)

    def test_manual_unread_is_personal_and_preserves_actual_read_history(self):
        room = self.group()
        self.client.force_authenticate(self.bob)
        message = self.send(room, 'Already read').data['id']
        self.client.force_authenticate(self.alice)
        read_url = self.url(f'conversations/{room}/read/')
        self.client.post(read_url, {'message_ids': [message]}, format='json')
        member = Participant.objects.get(conversation_id=room, user=self.alice)
        cursor = member.last_read_id
        prefs = self.url(f'conversations/{room}/preferences/')
        self.assertEqual(self.client.patch(prefs, {'is_marked_unread': True}, format='json').status_code, 204)
        listed = self.client.get(self.url()).data
        self.assertEqual(listed['unread_count'], 1)
        self.assertTrue(listed['results'][0]['is_marked_unread'])
        member.refresh_from_db()
        self.assertEqual(member.last_read_id, cursor)
        self.assertEqual(self.history(room).data['first_unread_id'], None)
        self.client.force_authenticate(self.bob)
        self.assertFalse(self.client.get(self.url()).data['results'][0]['is_marked_unread'])
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.post(read_url, {'message_ids': []}, format='json').status_code, 200)
        self.assertEqual(self.client.get(self.url()).data['unread_count'], 0)

    def test_dismissing_manual_unread_never_reads_unseen_messages(self):
        room = self.group()
        self.client.force_authenticate(self.bob)
        message = self.send(room).data['id']
        self.client.force_authenticate(self.alice)
        self.client.patch(self.url(f'conversations/{room}/preferences/'), {'is_marked_unread': True}, format='json')
        response = self.client.post(self.url(f'conversations/{room}/read/'), {'message_ids': []}, format='json')
        self.assertLess(response.data['last_read_id'], message)
        listed = self.client.get(self.url()).data['results'][0]
        self.assertFalse(listed['is_marked_unread'])
        self.assertEqual(listed['unread_count'], 1)

    def test_empty_chat_can_be_marked_unread_and_clear_removes_reminder(self):
        room = self.group()
        prefs = self.url(f'conversations/{room}/preferences/')
        self.client.patch(prefs, {'is_marked_unread': True}, format='json')
        self.assertEqual(self.client.get(self.url() + '&compact=1').data['unread_count'], 1)
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.assertEqual(self.client.get(self.url()).data['unread_count'], 0)
        self.client.force_authenticate(self.outsider)
        path = self.url(f'conversations/{room}/preferences/', self.other_company)
        self.assertEqual(self.client.patch(path, {'is_marked_unread': True}, format='json').status_code, 404)

    def test_room_search_finds_shared_product_sku_name_and_message_authors(self):
        room = self.group()
        product = self.product(self.company, name='Special fabric', sku='UNIQUE-478')
        sent = self.reference_message(room, 'product', product.pk).data['id']
        self.client.force_authenticate(self.bob)
        self.send(room, 'Message by a former participant')
        self.client.force_authenticate(self.alice)
        self.update(room, user_ids=[self.alice.pk])
        for query in ['UNIQUE-478', 'Special', 'bob']:
            response = self.client.get(self.url(), {'company_id': self.company.pk, 'q': query})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertIn(room, [row['id'] for row in response.data['results']])
        response = self.client.get(self.url(f'conversations/{room}/messages/') + '&q=alice')
        self.assertIn(sent, [row['id'] for row in response.data['results']])
        self.client.delete(self.message_url(room, sent))
        self.assertEqual(self.client.get(self.url() + '&q=UNIQUE-478').data['results'], [])

    def test_room_reference_search_respects_recipient_permissions_and_personal_clear(self):
        room = self.group()
        product = self.product(self.company, name='Private fabric', sku='RESTRICTED-941')
        self.reference_message(room, 'product', product.pk)
        self.client.force_authenticate(self.bob)
        role = self.bob.access_role
        from users.models import AccessRole
        restricted = AccessRole.objects.create(company=self.company, name='No reference access')
        self.bob.access_role = restricted; self.bob.save(update_fields=['access_role'])
        self.assertEqual(self.client.get(self.url() + '&q=RESTRICTED-941').data['results'], [])
        self.bob.access_role = role; self.bob.save(update_fields=['access_role'])
        self.assertEqual(self.client.get(self.url() + '&q=RESTRICTED-941').data['results'][0]['id'], room)
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.assertEqual(self.client.get(self.url() + '&q=RESTRICTED-941').data['results'], [])

    def test_conversation_paging_search_and_compact_notifications(self):
        for index in range(5):
            self.create_room(is_group=True, title=f'Team {index}')
        response = self.client.get(self.url() + '&limit=2').data
        self.assertEqual(len(response['results']), 2)
        self.assertEqual(response['total_count'], 5)
        self.assertTrue(response['has_more'])
        following = self.client.get(self.url() + '&limit=2&offset=2').data
        self.assertFalse({room['id'] for room in response['results']} & {room['id'] for room in following['results']})
        searched = self.client.get(self.url() + '&q=Team%203').data
        self.assertEqual([room['title'] for room in searched['results']], ['Team 3'])
        compact = self.client.get(self.url() + '&compact=1').data
        self.assertEqual(compact['results'], [])
        self.assertNotIn('participants', compact['notifications'][0])

    def test_related_discussions_never_reveal_another_private_chat(self):
        product = self.product(self.company)
        shared = self.create_room().data['id']
        private = self.create_room([self.carol.pk]).data['id']
        self.reference_message(shared, 'product', product.pk)
        self.reference_message(private, 'product', product.pk)
        self.client.force_authenticate(self.bob)
        data = self.client.get(self.url('related/') + f'&reference_type=product&reference_id={product.pk}').data
        self.assertEqual([room['id'] for room in data['results']], [shared])
        exists_url = self.url('related/') + f'&exists=1&reference_type=product&reference_id={product.pk}'
        self.assertEqual(self.client.get(exists_url).data, {'has_discussions': True})
        self.client.post(self.url(f'conversations/{shared}/clear/'))
        self.assertEqual(self.client.get(exists_url).data, {'has_discussions': False})

    def test_related_history_opens_at_the_latest_matching_old_reference(self):
        product = self.product(self.company)
        room = self.create_room().data['id']
        self.reference_message(room, 'product', product.pk)
        anchor = self.reference_message(room, 'product', product.pk).data['id']
        Message.objects.filter(conversation_id=room).update(created_at=timezone.now() - timedelta(days=60))
        Message.objects.bulk_create([Message(conversation_id=room, sender=self.alice, text=f'Later {index}', client_id=uuid.uuid4()) for index in range(80)])
        response = self.client.get(self.url(f'conversations/{room}/messages/') + f'&reference_type=product&reference_id={product.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['focus_id'], anchor)
        self.assertIn(anchor, [row['id'] for row in response.data['results']])
        self.assertTrue(response.data['has_newer'])
        self.assertNotIn(Message.objects.filter(conversation_id=room).last().pk, [row['id'] for row in response.data['results']])

    def test_related_history_cannot_jump_to_hidden_deleted_or_unauthorized_content(self):
        product = self.product(self.company)
        room = self.create_room().data['id']
        message = self.reference_message(room, 'product', product.pk).data['id']
        path = self.url(f'conversations/{room}/messages/') + f'&reference_type=product&reference_id={product.pk}'
        self.client.force_authenticate(self.bob)
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.assertEqual(self.client.get(path).status_code, 404)
        self.client.force_authenticate(self.carol)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.client.force_authenticate(self.alice)
        self.client.delete(self.message_url(room, message))
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_deleted_preview_flag_does_not_confuse_identical_user_text(self):
        room = self.create_room().data['id']
        message = self.send(room, 'Сообщение удалено').data['id']
        self.assertFalse(self.client.get(self.url()).data['results'][0]['last_message_deleted'])
        reply = self.reply(room, message).data
        self.assertFalse(reply['reply']['deleted'])
        self.client.delete(self.message_url(room, message))
        self.assertTrue(self.client.get(self.message_url(room, reply['id'])).data['reply']['deleted'])

    def test_related_exists_for_product_and_counterparty_requires_visible_live_links(self):
        product = self.product(self.company)
        room = self.create_room().data['id']
        for kind, pk in [('product', product.pk), ('counterparty', product.supplier_id)]:
            url = self.url('related/') + f'&exists=1&reference_type={kind}&reference_id={pk}'
            self.assertEqual(self.client.get(url).data, {'has_discussions': False})
            message = self.reference_message(room, kind, pk).data['id']
            self.assertEqual(self.client.get(url).data, {'has_discussions': True})
            context = self.client.get(self.url(f'conversations/{room}/messages/') + f'&reference_type={kind}&reference_id={pk}')
            self.assertEqual(context.data['focus_id'], message)
            self.client.patch(self.url(f'conversations/{room}/preferences/'), {'is_archived': True}, format='json')
            self.assertEqual(self.client.get(url).data, {'has_discussions': True})
            self.client.delete(self.message_url(room, message))
            self.assertEqual(self.client.get(url).data, {'has_discussions': False})

    def test_related_exists_checks_company_and_record_permissions(self):
        product = self.product(self.company)
        foreign = self.product(self.other_company)
        room = self.create_room().data['id']
        self.reference_message(room, 'product', product.pk)
        url = self.url('related/') + f'&exists=1&reference_type=product&reference_id={product.pk}'
        foreign_url = self.url('related/') + f'&exists=1&reference_type=product&reference_id={foreign.pk}'
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        from users.models import AccessRole
        self.bob.access_role = AccessRole.objects.create(company=self.company, name='No products')
        self.bob.save(update_fields=['access_role'])
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_total_storage_above_five_gib_does_not_block_files_or_retries(self):
        self.private_storage()
        room = self.group()
        # Simulate accumulated uploads using metadata, without creating gigabytes on disk.
        history = Message.objects.bulk_create([
            Message(conversation_id=room, sender=self.alice, text='Old files', client_id=uuid.uuid4()) for _ in range(120)
        ])
        Attachment.objects.bulk_create([
            Attachment(message=message, file=f'old/{message.pk}/{index}', name='old.txt', size=10 * 1024 ** 2, content_type='text/plain')
            for message in history for index in range(5)
        ])
        info = self.client.get(self.url('storage/')).data
        self.assertGreater(info['used_bytes'], 5 * 1024 ** 3)
        self.assertNotIn('quota_bytes', info)
        key = str(uuid.uuid4())
        first = self.upload(room, [SimpleUploadedFile('one.txt', b'1234567890')], key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.upload(room, [SimpleUploadedFile('two.txt', b'1234567890')]).status_code, 201)
        self.assertEqual(self.upload(room, [SimpleUploadedFile('one.txt', b'1234567890')], key).status_code, 200)
        self.assertEqual(self.send(room).status_code, 201)
        self.assertEqual(self.client.patch(self.url('storage/'), {'deleted_file_retention_days': 30}).status_code, 403)

    def test_cleanup_dry_run_and_retention_never_remove_active_files(self):
        self.private_storage()
        room = self.group()
        active = self.upload(room, [SimpleUploadedFile('active.txt', b'keep')]).data
        removed = self.upload(room, [SimpleUploadedFile('removed.txt', b'remove')]).data
        self.client.delete(self.message_url(room, removed['id']))
        Message.objects.filter(pk=removed['id']).update(deleted_at=timezone.now() - timedelta(days=31))
        output = io.StringIO()
        call_command('cleanup_chat_uploads', company=self.company.pk, stdout=output)
        attachment = Attachment.objects.get(message_id=removed['id'])
        self.assertTrue(attachment.file.storage.exists(attachment.file.name))
        call_command('cleanup_chat_uploads', company=self.company.pk, apply=True, stdout=io.StringIO())
        attachment.refresh_from_db()
        self.assertIsNotNone(attachment.purged_at)
        self.assertFalse(attachment.file.storage.exists(attachment.file.name))
        kept = Attachment.objects.get(message_id=active['id'])
        self.assertTrue(kept.file.storage.exists(kept.file.name))

    def test_private_backup_contains_metadata_uploads_checksums_and_refuses_overwrite(self):
        self.private_storage()
        room = self.group()
        self.upload(room, [SimpleUploadedFile('notes.txt', b'backup content')])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'chat.zip'
            call_command('backup_chat', output=str(target), stdout=io.StringIO())
            with ZipFile(target) as archive:
                manifest = json.loads(archive.read('manifest.json'))
                file = manifest['files'][0]
                content = archive.read(file['entry'])
                self.assertEqual(content, b'backup content')
                self.assertEqual(file['sha256'], hashlib.sha256(content).hexdigest())
                self.assertIn('chat.message', archive.read('chat.json').decode())
                self.assertNotIn('users.customuser', archive.read('chat.json').decode())
            with self.assertRaises(CommandError):
                call_command('backup_chat', output=str(target), stdout=io.StringIO())
