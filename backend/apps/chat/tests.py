import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Company, CompanyMembership
from .models import Conversation, Message, Participant


class ChatTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.company = Company.objects.create(name='Chat company')
        self.other_company = Company.objects.create(name='Other chat company')
        self.alice = self.employee('alice', self.company)
        self.bob = self.employee('bob', self.company)
        self.carol = self.employee('carol', self.company)
        self.outsider = self.employee('outsider', self.other_company)
        self.client.force_authenticate(self.alice)

    def employee(self, name, company):
        user = get_user_model().objects.create_user(
            username=name, email=f'{name}@example.com', company=company,
            is_email_verified=True, first_name=name.title(),
        )
        CompanyMembership.objects.create(user=user, company=company)
        return user

    def url(self, path='conversations/', company=None):
        return f'/api/chat/{path}?company_id={(company or self.company).pk}'

    def create_room(self, ids=None, **kwargs):
        return self.client.post(self.url(), {'user_ids': ids or [self.bob.pk], **kwargs}, format='json')

    def send(self, room, text='Hello', client_id=None):
        return self.client.post(self.url(f'conversations/{room}/messages/'),
                                {'text': text, 'client_id': client_id or str(uuid.uuid4())}, format='json')

    def test_employee_directory_includes_active_members_even_before_email_verification(self):
        CompanyMembership.objects.filter(user=self.carol).update(status='disabled')
        pending = self.employee('pending', self.company)
        pending.is_email_verified = False
        pending.save()
        response = self.client.get(self.url('employees/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({p['id'] for p in response.data}, {self.bob.pk, pending.pk})

    def test_group_employee_search_excludes_members_before_applying_limit(self):
        room = self.create_room(is_group=True, title='Team').data['id']
        self.bob.first_name = 'Same A'; self.bob.save(update_fields=['first_name'])
        self.carol.first_name = 'Same B'; self.carol.save(update_fields=['first_name'])
        response = self.client.get(self.url('employees/') + f'&exclude_conversation={room}&q=Same&limit=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [self.carol.pk])
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(self.url('employees/', self.other_company) + f'&exclude_conversation={room}').status_code, 404)

    def test_active_unverified_employee_can_receive_direct_and_group_messages(self):
        self.bob.is_email_verified = False
        self.bob.save(update_fields=['is_email_verified'])
        for options in [{}, {'is_group': True, 'title': 'Sales'}]:
            response = self.create_room(**options)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(self.send(response.data['id']).status_code, 201)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_globally_inactive_employee_is_not_available_as_recipient(self):
        self.bob.is_active = False
        self.bob.save(update_fields=['is_active'])
        response = self.client.get(self.url('employees/'))
        self.assertNotIn(self.bob.pk, [person['id'] for person in response.data])
        self.assertEqual(self.create_room().status_code, 400)

    def test_employee_can_be_in_another_active_company_and_still_receive_chat(self):
        CompanyMembership.objects.create(user=self.bob, company=self.other_company)
        self.bob.company = self.other_company
        self.bob.save()
        self.assertEqual(self.create_room().status_code, 201)

    def test_direct_conversation_is_reused_in_both_directions(self):
        room = self.create_room().data['id']
        self.client.force_authenticate(self.bob)
        response = self.create_room([self.alice.pk])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], room)
        self.assertEqual(Participant.objects.count(), 2)

    def test_same_people_have_separate_chats_per_company(self):
        first = self.create_room().data['id']
        for user in [self.alice, self.bob]:
            CompanyMembership.objects.create(user=user, company=self.other_company)
            user.company = self.other_company
            user.save()
        response = self.client.post(self.url(company=self.other_company), {'user_ids': [self.bob.pk]}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.data['id'], first)
        self.assertEqual(self.client.get(self.url(f'conversations/{first}/messages/', self.other_company)).status_code, 404)

    def test_cross_company_creation_is_rejected(self):
        self.assertEqual(self.create_room([self.outsider.pk]).status_code, 400)
        self.assertEqual(self.create_room([self.bob.pk, self.outsider.pk], is_group=True, title='Sales').status_code, 400)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_group_only_includes_selected_people_and_creator(self):
        response = self.create_room(is_group=True, title='Sales')
        self.assertEqual(response.status_code, 201)
        room = Conversation.objects.get(pk=response.data['id'])
        self.assertTrue(room.is_group)
        self.assertEqual(set(room.participants.values_list('user_id', flat=True)), {self.alice.pk, self.bob.pk})
        self.client.force_authenticate(self.carol)
        self.assertEqual(self.client.get(self.url()).data['results'], [])
        self.assertEqual(self.client.get(self.url(f'conversations/{room.pk}/messages/')).status_code, 404)
        self.assertEqual(self.send(room.pk).status_code, 404)

    def test_company_admin_does_not_see_other_peoples_messages(self):
        room = self.create_room().data['id']
        self.carol.is_company_admin = True
        self.carol.save()
        self.client.force_authenticate(self.carol)
        self.assertEqual(self.client.get(self.url()).data['results'], [])
        self.assertEqual(self.send(room).status_code, 404)

    def test_group_validation(self):
        self.assertEqual(self.create_room(is_group=True, title=' ').status_code, 400)
        self.assertEqual(self.create_room([self.alice.pk]).status_code, 400)
        self.assertEqual(self.create_room([self.bob.pk, self.carol.pk]).status_code, 400)

    def test_message_validation_retry_and_plain_text(self):
        room = self.create_room().data['id']
        self.assertEqual(self.send(room, ' ').status_code, 400)
        self.assertEqual(self.send(room, 'x' * 5001).status_code, 400)
        self.assertEqual(self.send(room, client_id='invalid').status_code, 400)
        key = str(uuid.uuid4())
        first = self.send(room, '<script>alert(1)</script>', key)
        retry = self.send(room, 'retry changed content', key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(first.data['id'], retry.data['id'])
        self.assertEqual(Message.objects.get().text, '<script>alert(1)</script>')

    def test_unread_counts_and_read_cursor_are_monotonic(self):
        room = self.create_room().data['id']
        first = self.send(room).data['id']
        second = self.send(room, 'Second').data['id']
        self.assertEqual(self.client.get(self.url()).data['unread_count'], 0)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(self.url()).data['unread_count'], 2)
        for message_id in [second, first]:
            response = self.client.post(self.url(f'conversations/{room}/read/'), {'message_id': message_id})
            self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(self.url()).data['unread_count'], 0)
        self.assertEqual(Participant.objects.get(conversation_id=room, user=self.bob).last_read_id, second)

    def test_cannot_mark_a_message_from_another_room_as_read(self):
        first = self.create_room().data['id']
        second = self.create_room([self.carol.pk]).data['id']
        message = self.send(second).data['id']
        self.assertEqual(self.client.post(self.url(f'conversations/{first}/read/'), {'message_id': message}).status_code, 404)

    def test_history_pagination_and_incremental_fetch(self):
        room = self.create_room().data['id']
        Message.objects.bulk_create([Message(conversation_id=room, sender=self.bob, text=str(i), client_id=uuid.uuid4()) for i in range(65)])
        latest = self.client.get(self.url(f'conversations/{room}/messages/')).data
        self.assertEqual(len(latest['results']), 50)
        self.assertTrue(latest['has_more'])
        first_id = latest['results'][0]['id']
        older = self.client.get(self.url(f'conversations/{room}/messages/') + f'&before={first_id}').data
        self.assertEqual(len(older['results']), 15)
        self.assertFalse(older['has_more'])
        ids = [m['id'] for m in older['results'] + latest['results']]
        self.assertEqual(ids, sorted(set(ids)))
        updates = self.client.get(self.url(f'conversations/{room}/messages/') + f'&after={ids[-2]}').data
        self.assertEqual([m['id'] for m in updates['results']], [ids[-1]])
        self.assertEqual(self.client.get(self.url(f'conversations/{room}/messages/') + '&before=no').status_code, 400)

    def test_disabled_membership_cannot_read_send_or_create(self):
        room = self.create_room().data['id']
        CompanyMembership.objects.filter(user=self.alice).update(status='disabled')
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.send(room).status_code, 403)
        self.assertEqual(self.create_room().status_code, 403)

    def test_unverified_user_cannot_chat(self):
        self.alice.is_email_verified = False
        self.alice.save()
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_company_context_is_required_and_stale_requests_are_rejected(self):
        self.assertEqual(self.client.get('/api/chat/conversations/').status_code, 409)
        self.assertEqual(self.client.get(self.url(company=self.other_company)).status_code, 409)
        self.assertEqual(self.client.post(self.url(company=self.other_company), {'user_ids': [self.bob.pk]}).status_code, 409)

    def test_outsider_cannot_read_send_or_mark_read_even_knowing_ids(self):
        room = self.create_room().data['id']
        message = self.send(room).data['id']
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(self.url(company=self.other_company)).data['results'], [])
        path = f'conversations/{room}/'
        self.assertEqual(self.client.get(self.url(path + 'messages/', self.other_company)).status_code, 404)
        self.assertEqual(self.client.post(self.url(path + 'messages/', self.other_company), {'text': 'attack', 'client_id': str(uuid.uuid4())}).status_code, 404)
        self.assertEqual(self.client.post(self.url(path + 'read/', self.other_company), {'message_id': message}).status_code, 404)

    def test_anonymous_cannot_access_chat(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url()).status_code, 401)

    def test_existing_cookie_authentication_requires_csrf_on_send(self):
        from django.conf import settings
        from rest_framework.test import APIClient
        room = self.create_room().data['id']
        client = APIClient(enforce_csrf_checks=True)
        client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(RefreshToken.for_user(self.alice).access_token)
        self.assertEqual(client.get(self.url()).status_code, 200)
        response = client.post(self.url(f'conversations/{room}/messages/'), {'text': 'no csrf', 'client_id': str(uuid.uuid4())})
        self.assertEqual(response.status_code, 403)
