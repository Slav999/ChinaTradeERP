import io
import tempfile
import uuid
from unittest.mock import patch

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from products.models import Product
from counterparties.models import Counterparty
from customer_orders.models import CustomerOrder, CustomerOrderStatus
from supplier_orders.models import SupplierOrder, SupplierOrderStatus
from users.models import AccessRole
from .models import Attachment, Conversation, Participant
from .tests import ChatTests


class ChatFeatureTests(APITestCase):
    setUp = ChatTests.setUp
    employee = ChatTests.employee
    url = ChatTests.url
    create_room = ChatTests.create_room
    send = ChatTests.send

    def group(self):
        return self.create_room(is_group=True, title='Sales').data['id']

    def update(self, room, **values):
        return self.client.patch(self.url(f'conversations/{room}/'), values, format='json')

    def history(self, room):
        return self.client.get(self.url(f'conversations/{room}/messages/'))

    def test_creator_can_rename_add_and_remove_members(self):
        room = self.group()
        old = self.send(room, 'Before Carol joins').data['id']
        response = self.update(room, title='New Sales', user_ids=[self.alice.pk, self.bob.pk, self.carol.pk])
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Conversation.objects.get(pk=room).title, 'New Sales')
        self.client.force_authenticate(self.carol)
        self.assertEqual([m['id'] for m in self.history(room).data['results']], [old])
        self.assertEqual(self.client.get(self.url()).data['unread_count'], 0)
        self.client.force_authenticate(self.alice)
        new = self.send(room, 'After Carol joins').data['id']
        self.client.force_authenticate(self.carol)
        self.assertEqual([m['id'] for m in self.history(room).data['results']], [old, new])
        self.assertEqual(self.client.post(self.url(f'conversations/{room}/read/'), {'message_id': old}).status_code, 204)
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.update(room, user_ids=[self.alice.pk, self.bob.pk]).status_code, 204)
        self.client.force_authenticate(self.carol)
        self.assertEqual(self.history(room).status_code, 404)
        self.assertEqual(self.send(room).status_code, 404)

    def test_only_creator_manages_group_even_if_member_is_company_admin(self):
        room = self.group()
        self.bob.is_company_admin = True
        self.bob.save()
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.update(room, title='Hijack').status_code, 403)
        self.assertEqual(self.client.delete(self.url(f'conversations/{room}/')).status_code, 403)

    def test_cannot_remove_creator_add_outsider_or_edit_direct_chat(self):
        room = self.group()
        self.assertEqual(self.update(room, user_ids=[self.bob.pk]).status_code, 400)
        self.assertEqual(self.update(room, user_ids=[self.alice.pk, self.outsider.pk]).status_code, 400)
        self.assertEqual(Participant.objects.filter(conversation_id=room).count(), 2)
        direct = self.create_room().data['id']
        self.assertEqual(self.update(direct, user_ids=[self.alice.pk]).status_code, 403)

    def test_readded_member_can_read_complete_history(self):
        room = self.group()
        self.send(room, 'Old')
        self.update(room, user_ids=[self.alice.pk])
        self.send(room, 'While removed')
        self.update(room, user_ids=[self.alice.pk, self.bob.pk])
        self.client.force_authenticate(self.bob)
        self.assertEqual([m['text'] for m in self.history(room).data['results']], ['Old', 'While removed'])

    def test_adding_colleague_does_not_reset_existing_members_personal_clear(self):
        room = self.group()
        self.send(room, 'Before clear')
        self.client.force_authenticate(self.bob)
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.client.force_authenticate(self.alice)
        self.update(room, user_ids=[self.alice.pk, self.bob.pk, self.carol.pk])
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.history(room).data['results'], [])
        self.client.force_authenticate(self.carol)
        self.assertEqual([m['text'] for m in self.history(room).data['results']], ['Before clear'])

    def test_clear_is_personal_and_unread_and_preview_do_not_leak_hidden_history(self):
        room = self.group()
        old = self.send(room, 'Private old preview').data['id']
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.post(self.url(f'conversations/{room}/clear/')).status_code, 204)
        self.assertEqual(self.history(room).data['results'], [])
        listed = self.client.get(self.url()).data
        self.assertEqual(listed['unread_count'], 0)
        self.assertEqual(listed['results'][0]['last_text'], '')
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.history(room).data['results'][0]['id'], old)
        self.send(room, 'New')
        self.client.force_authenticate(self.bob)
        self.assertEqual([m['text'] for m in self.history(room).data['results']], ['New'])

    def test_delete_group_revokes_everyone_and_preserves_data(self):
        room = self.group()
        self.send(room)
        self.assertEqual(self.client.delete(self.url(f'conversations/{room}/')).status_code, 204)
        self.assertTrue(Conversation.objects.get(pk=room).is_deleted)
        for user in [self.alice, self.bob]:
            self.client.force_authenticate(user)
            self.assertEqual(self.history(room).status_code, 404)
            self.assertEqual(self.send(room).status_code, 404)
            self.assertEqual(self.client.get(self.url()).data['results'], [])

    def test_delete_direct_is_personal_and_new_message_brings_it_back(self):
        room = self.create_room().data['id']
        self.send(room, 'Old')
        self.assertEqual(self.client.delete(self.url(f'conversations/{room}/')).status_code, 204)
        self.assertEqual(self.client.get(self.url()).data['results'], [])
        self.client.force_authenticate(self.bob)
        self.assertEqual(len(self.history(room).data['results']), 1)
        self.send(room, 'Return')
        self.client.force_authenticate(self.alice)
        self.assertEqual(len(self.client.get(self.url()).data['results']), 1)
        self.assertEqual([m['text'] for m in self.history(room).data['results']], ['Return'])

    def upload(self, room, files, client_id=None):
        return self.client.post(self.url(f'conversations/{room}/messages/'),
                                {'client_id': client_id or str(uuid.uuid4()), 'files': files}, format='multipart')

    def private_storage(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch.object(Attachment._meta.get_field('file'), 'storage', FileSystemStorage(location=directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_upload_is_private_idempotent_and_removed_member_loses_download(self):
        self.private_storage()
        room = self.group()
        key = str(uuid.uuid4())
        first = self.upload(room, [SimpleUploadedFile('report.pdf', b'%PDF-1.7\nexample')], key)
        self.assertEqual(first.status_code, 201, first.data)
        retry = self.upload(room, [SimpleUploadedFile('report.pdf', b'%PDF-1.7\nexample')], key)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(Attachment.objects.count(), 1)
        attachment = first.data['attachments'][0]
        self.assertNotIn('url', attachment)
        path = self.url(f'conversations/{room}/attachments/{attachment["id"]}/')
        self.client.force_authenticate(self.bob)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(b''.join(response.streaming_content))
        self.client.force_authenticate(self.carol)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.client.force_authenticate(self.alice)
        self.update(room, user_ids=[self.alice.pk])
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_missing_upload_returns_not_found_instead_of_server_error(self):
        self.private_storage()
        room = self.group()
        uploaded = self.upload(room, [SimpleUploadedFile('lost.txt', b'hello')]).data
        attachment = Attachment.objects.get(pk=uploaded['attachments'][0]['id'])
        attachment.file.delete(save=False)
        response = self.client.get(self.url(f'conversations/{room}/attachments/{attachment.pk}/'))
        self.assertEqual(response.status_code, 404)

    def test_image_preview_and_clear_block_old_attachment(self):
        self.private_storage()
        room = self.group()
        image = io.BytesIO()
        Image.new('RGB', (4, 4), 'blue').save(image, format='PNG')
        response = self.upload(room, [SimpleUploadedFile('screenshot.png', image.getvalue())])
        self.assertEqual(response.status_code, 201, response.data)
        path = self.url(f'conversations/{room}/attachments/{response.data["attachments"][0]["id"]}/') + '&preview=1'
        preview = self.client.get(path)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview['Content-Type'], 'image/png')
        self.assertIn('inline;', preview['Content-Disposition'])
        self.assertTrue(b''.join(preview.streaming_content))
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_invalid_files_cannot_create_partial_message(self):
        self.private_storage()
        room = self.group()
        for name in ['malware.exe', 'pretend.png', 'pretend.pdf', 'pretend.docx']:
            response = self.upload(room, [SimpleUploadedFile(name, b'not a document')])
            self.assertEqual(response.status_code, 400, (name, response.data))
        response = self.upload(room, [SimpleUploadedFile(f'{i}.txt', b'hello') for i in range(6)])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Conversation.objects.get(pk=room).messages.count(), 0)

    def test_per_upload_size_limits_remain_without_a_company_quota(self):
        from rest_framework.exceptions import ValidationError
        from .uploads import validate_uploads
        oversized = SimpleUploadedFile('large.txt', b'x')
        oversized.size = 20 * 1024 ** 2 + 1
        combined = [SimpleUploadedFile(f'{index}.txt', b'x') for index in range(3)]
        for file in combined:
            file.size = 18 * 1024 ** 2
        for files in [[oversized], combined]:
            with self.assertRaises(ValidationError):
                validate_uploads(files)

    def reference_message(self, room, kind, pk):
        return self.client.post(self.url(f'conversations/{room}/messages/'),
                                {'client_id': str(uuid.uuid4()), 'reference_type': kind, 'reference_id': pk}, format='json')

    def product(self, company, name='Fabric', sku='FAB'):
        supplier = Counterparty.objects.create(company=company, name='Supplier', type='china', is_supplier=True)
        return Product.objects.create(company=company, name=name, sku=sku, supplier=supplier)

    def test_share_product_search_is_company_scoped_and_has_no_prices(self):
        product = self.product(self.company)
        foreign = self.product(self.other_company, name='Secret', sku='SECRET')
        room = self.create_room().data['id']
        response = self.reference_message(room, 'product', product.pk)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['reference']['title'], 'Fabric')
        self.assertNotIn('sale_price', response.data['reference'])
        self.assertEqual(self.reference_message(room, 'product', foreign.pk).status_code, 404)
        search = self.client.get(self.url('references/') + '&type=product&search=FAB')
        self.assertEqual([row['id'] for row in search.data], [product.pk])

    def test_reference_metadata_is_checked_again_for_recipient_permissions(self):
        product = self.product(self.company)
        room = self.create_room().data['id']
        self.reference_message(room, 'product', product.pk)
        role = AccessRole.objects.create(company=self.company, name='No product access')
        self.bob.access_role = role
        self.bob.save()
        self.client.force_authenticate(self.bob)
        reference = self.history(room).data['results'][0]['reference']
        self.assertTrue(reference['unavailable'])
        self.assertNotIn('route', reference)
        self.assertNotIn('Fabric', str(reference))
        self.assertEqual(self.client.get(self.url('references/') + '&type=product').status_code, 403)
        self.assertEqual(self.reference_message(room, 'product', product.pk).status_code, 403)

    def test_customer_supplier_and_sample_orders_have_working_routes(self):
        counterparty = Counterparty.objects.create(company=self.company, name='Partner', type='local', is_customer=True, is_supplier=True)
        customer_status = CustomerOrderStatus.objects.create(company=self.company, name='New')
        supplier_status = SupplierOrderStatus.objects.create(company=self.company, name='New')
        customer = CustomerOrder.objects.create(company=self.company, customer=counterparty, status=customer_status)
        supplier = SupplierOrder.objects.create(company=self.company, supplier=counterparty, status=supplier_status)
        sample = SupplierOrder.objects.create(company=self.company, supplier=counterparty, status=supplier_status, is_sample=True)
        room = self.create_room().data['id']
        for kind, obj, prefix in [('customer_order', customer, '/customer-orders'), ('supplier_order', supplier, '/supplier-orders'), ('supplier_order', sample, '/samples-trips')]:
            related = self.url('related/') + f'&exists=1&reference_type={kind}&reference_id={obj.pk}'
            self.assertEqual(self.client.get(related).data, {'has_discussions': False})
            response = self.reference_message(room, kind, obj.pk)
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['reference']['route']['path'], f'{prefix}/{obj.pk}')
            self.assertEqual(self.client.get(related).data, {'has_discussions': True})
            context = self.client.get(self.url(f'conversations/{room}/messages/') + f'&reference_type={kind}&reference_id={obj.pk}')
            self.assertEqual(context.data['focus_id'], response.data['id'])
            search = self.client.get(self.url('references/') + f'&type={kind}&search={obj.order_number}')
            self.assertIn(obj.pk, [row['id'] for row in search.data])
        self.assertIn(customer.pk, [row['id'] for row in self.client.get(self.url('references/') + '&type=customer_order&search=Partner').data])
        self.assertIn(supplier.pk, [row['id'] for row in self.client.get(self.url('references/') + '&type=supplier_order&search=Partner').data])

    def test_reference_search_requires_query_and_is_limited_to_five_matches(self):
        product = self.product(self.company, name='Shared fabric')
        for index in range(7):
            Product.objects.create(company=self.company, name=f'Shared fabric {index}', sku=f'SHARED-{index}', supplier=product.supplier)
        self.assertEqual(self.client.get(self.url('references/') + '&type=product').data, [])
        self.assertEqual(self.client.get(self.url('references/') + '&type=product&search=%20').data, [])
        response = self.client.get(self.url('references/') + '&type=product&search=Shared')
        self.assertNotIn(product.pk, [row['id'] for row in response.data])
        room = self.create_room().data['id']
        sent = self.reference_message(room, 'product', product.pk).data['id']
        history = self.client.get(self.url(f'conversations/{room}/messages/') + '&tab=references&q=Shared')
        self.assertEqual(history.status_code, 200)
        self.assertEqual([row['id'] for row in history.data['results']], [sent])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5)

    def test_mentions_use_group_nicknames_and_utf16_offsets_without_matching_email(self):
        room = self.group()
        self.update(room, user_ids=[self.alice.pk, self.bob.pk, self.carol.pk])
        text = '😀 @bob, обсуди с @carol. bob@example.com @outsider'
        response = self.send(room, text)
        self.assertEqual(response.status_code, 201)
        mentions = response.data['mentions']
        self.assertEqual([person['id'] for person in mentions], [self.bob.pk, self.carol.pk])
        encoded = text.encode('utf-16-le')
        for person in mentions:
            self.assertEqual(encoded[person['start'] * 2:person['end'] * 2].decode('utf-16-le'), '@' + person['username'])
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.history(room).data['results'][0]['mentions'], mentions)

    def test_added_member_can_download_old_group_files(self):
        self.private_storage()
        room = self.group()
        response = self.upload(room, [SimpleUploadedFile('old.txt', b'Old discussion notes')])
        attachment_id = response.data['attachments'][0]['id']
        self.update(room, user_ids=[self.alice.pk, self.bob.pk, self.carol.pk])
        self.client.force_authenticate(self.carol)
        download = self.client.get(self.url(f'conversations/{room}/attachments/{attachment_id}/'))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b''.join(download.streaming_content), b'Old discussion notes')

    def test_sound_marker_tracks_incoming_messages_not_own_messages(self):
        room = self.create_room().data['id']
        own = self.send(room).data['id']
        listed = self.client.get(self.url()).data['results'][0]
        self.assertEqual(listed['last_message_id'], own)
        self.assertIsNone(listed['last_incoming_message_id'])
        self.client.force_authenticate(self.bob)
        incoming = self.send(room).data['id']
        self.client.force_authenticate(self.alice)
        listed = self.client.get(self.url()).data['results'][0]
        self.assertEqual(listed['last_incoming_message_id'], incoming)
        self.assertEqual(listed['unread_count'], 1)

    def test_unread_mention_label_exists_before_opening_and_clears_after_read(self):
        room = self.group()
        message = self.send(room, '😀 @bob, проверь заказ').data['id']
        self.client.force_authenticate(self.bob)
        listed = self.client.get(self.url()).data['results'][0]
        self.assertEqual(listed['unread_mention_count'], 1)
        self.client.post(self.url(f'conversations/{room}/read/'), {'message_id': message})
        self.assertEqual(self.client.get(self.url()).data['results'][0]['unread_mention_count'], 0)

    def test_mention_marker_ignores_email_similar_nicknames_and_personally_cleared_text(self):
        room = self.group()
        self.send(room, 'bob@example.com @bobby @bob-extra')
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(self.url()).data['results'][0]['unread_mention_count'], 0)
        self.client.force_authenticate(self.alice)
        self.send(room, '@bob, привет!')
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(self.url()).data['results'][0]['unread_mention_count'], 1)
        self.client.post(self.url(f'conversations/{room}/clear/'))
        self.assertEqual(self.client.get(self.url()).data['results'][0]['unread_mention_count'], 0)

    def test_nonparticipant_does_not_get_mention_metadata(self):
        room = self.group()
        self.send(room, '@carol')
        self.client.force_authenticate(self.carol)
        self.assertEqual(self.client.get(self.url()).data['results'], [])
