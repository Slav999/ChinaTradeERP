from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from users.models import Company, CompanyMembership, Department, Invitation


class InvitationTestSetup:
    def setUp(self):
        self.company = Company.objects.create(name='Invitation lifecycle')
        self.admin = get_user_model().objects.create_user(
            username='invite-admin', email='admin@example.com', password='StrongPass123',
            company=self.company, is_company_admin=True, is_email_verified=True,
        )
        self.company.created_by = self.admin
        self.company.save(update_fields=['created_by'])
        self.client.force_authenticate(self.admin)

    def invite(self, **kwargs):
        return Invitation.objects.create(
            company=self.company, email='employee@example.com', **kwargs,
        )


class InvitationLifecycleTests(InvitationTestSetup, APITestCase):
    def test_list_excludes_expired_and_other_company_invitations(self):
        expired = self.invite(expires_at=timezone.now() - timedelta(seconds=1))
        current = self.invite()
        other = Company.objects.create(name='Other company')
        Invitation.objects.create(company=other, email='other@example.com')
        response = self.client.get('/api/auth/invitations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [current.id])
        expired.refresh_from_db()
        self.assertEqual(expired.status, Invitation.STATUS_EXPIRED)

    @patch('users.serializers.send_invitation_email')
    def test_new_invitation_lasts_three_days_and_resend_revokes_previous(self, send_email):
        previous = self.invite()
        before = timezone.now()
        response = self.client.post('/api/auth/invitations/', {'email': previous.email})
        self.assertEqual(response.status_code, 201, response.data)
        current = Invitation.objects.get(pk=response.data['id'])
        self.assertGreaterEqual(current.expires_at, before + timedelta(days=3))
        self.assertLessEqual(current.expires_at, timezone.now() + timedelta(days=3))
        previous.refresh_from_db()
        self.assertEqual(previous.status, Invitation.STATUS_REVOKED)
        send_email.assert_called_once()

    def test_expired_link_cannot_be_previewed_or_accepted(self):
        token = Invitation.build_token()
        invitation = self.invite(expires_at=timezone.now() - timedelta(seconds=1))
        invitation.set_token(token)
        invitation.save()
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/auth/invitations/{token}/').status_code, 404)
        response = self.client.post('/api/auth/invitations/accept/', {'token': token})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.company.memberships.exists())

    def test_non_admin_cannot_invite_or_read_pending_invitations(self):
        self.invite()
        self.admin.is_company_admin = False
        self.admin.save(update_fields=['is_company_admin'])
        self.assertEqual(self.client.get('/api/auth/invitations/').data, [])
        response = self.client.post('/api/auth/invitations/', {'email': 'new@example.com'})
        self.assertEqual(response.status_code, 403)

    @patch('users.serializers.send_invitation_email')
    def test_resend_replaces_token_and_preserves_invitation_fields(self, send_email):
        department = Department.objects.create(company=self.company, name='Custom department')
        invitation = self.invite(department=department, position='Specialist')
        old_token = Invitation.build_token()
        invitation.set_token(old_token)
        invitation.save()
        response = self.client.post(f'/api/auth/invitations/{invitation.pk}/resend/')
        self.assertEqual(response.status_code, 201, response.data)
        replacement = Invitation.objects.get(pk=response.data['id'])
        self.assertEqual(replacement.department, department)
        self.assertEqual(replacement.position, 'Specialist')
        self.assertNotEqual(replacement.token_hash, invitation.token_hash)
        self.assertAlmostEqual((replacement.expires_at - timezone.now()).total_seconds(), 3 * 86400, delta=5)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, Invitation.STATUS_REVOKED)
        self.assertEqual(self.client.get(f'/api/auth/invitations/{old_token}/').status_code, 404)
        send_email.assert_called_once()

    @patch('users.serializers.send_invitation_email', side_effect=RuntimeError('Mail unavailable'))
    def test_failed_resend_keeps_original_invitation_valid(self, send_email):
        invitation = self.invite()
        original_hash = invitation.token_hash
        response = self.client.post(f'/api/auth/invitations/{invitation.pk}/resend/')
        self.assertEqual(response.status_code, 503)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, Invitation.STATUS_PENDING)
        self.assertEqual(invitation.token_hash, original_hash)
        self.assertEqual(Invitation.objects.count(), 1)

    def test_revoke_disables_acceptance_and_is_company_scoped(self):
        invitation = self.invite()
        token = Invitation.build_token()
        invitation.set_token(token)
        invitation.save()
        other_company = Company.objects.create(name='Not accessible')
        other = Invitation.objects.create(company=other_company, email='other@example.com')
        for action in ('revoke', 'resend'):
            self.assertEqual(self.client.post(f'/api/auth/invitations/{other.pk}/{action}/').status_code, 404)
        response = self.client.post(f'/api/auth/invitations/{invitation.pk}/revoke/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(f'/api/auth/invitations/{token}/').status_code, 404)
        self.assertEqual(self.client.post('/api/auth/invitations/accept/', {'token': token}).status_code, 400)

    def test_non_admin_cannot_manage_invitation_actions(self):
        invitation = self.invite()
        self.admin.is_company_admin = False
        self.admin.save(update_fields=['is_company_admin'])
        for action in ('revoke', 'resend'):
            self.assertEqual(self.client.post(f'/api/auth/invitations/{invitation.pk}/{action}/').status_code, 403)

    def test_expired_invitation_cannot_be_resent(self):
        invitation = self.invite(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.post(f'/api/auth/invitations/{invitation.pk}/resend/')
        self.assertEqual(response.status_code, 400)


class CompanyDepartmentTests(InvitationTestSetup, APITestCase):
    def test_manage_bilingual_department_and_keep_membership_on_archive(self):
        response = self.client.post('/api/auth/departments/', {
            'name': 'My department', 'translations': {'ru': 'Мой отдел', 'en': 'My department'},
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        department = Department.objects.get(pk=response.data['id'])
        membership = CompanyMembership.objects.create(user=self.admin, company=self.company, department=department)
        self.admin.department_ref = department
        self.admin.department = department.name
        self.admin.save(update_fields=['department_ref', 'department'])
        response = self.client.patch(f'/api/auth/departments/{department.pk}/', {
            'name': 'Updated', 'translations': {'ru': 'Обновлённый', 'en': 'Updated'},
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['translations']['ru'], 'Обновлённый')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.department, 'Updated')
        self.assertEqual(self.client.delete(f'/api/auth/departments/{department.pk}/').status_code, 204)
        membership.refresh_from_db()
        self.assertEqual(membership.department_id, department.pk)
        self.assertEqual(self.client.get('/api/auth/departments/').data, [])
        archived = self.client.get('/api/auth/departments/?include_archived=true').data
        self.assertEqual(archived[0]['id'], department.pk)
        self.assertTrue(archived[0]['is_archived'])
        response = self.client.post('/api/auth/invitations/', {'email': 'new@example.com', 'department': department.pk})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.patch(f'/api/auth/departments/{department.pk}/', {'is_archived': False}).status_code, 200)
        self.assertEqual(len(self.client.get('/api/auth/departments/').data), 1)

    def test_department_permissions_and_company_isolation(self):
        other = Company.objects.create(name='Other departments')
        department = Department.objects.create(company=other, name='Private')
        self.assertEqual(self.client.get('/api/auth/departments/').data, [])
        self.assertEqual(self.client.patch(f'/api/auth/departments/{department.pk}/', {'name': 'Stolen'}).status_code, 404)
        self.assertEqual(self.client.post('/api/auth/invitations/', {
            'email': 'new@example.com', 'department': department.pk,
        }).status_code, 400)
        own = Department.objects.create(company=self.company, name='Own')
        self.admin.is_company_admin = False
        self.admin.save(update_fields=['is_company_admin'])
        self.assertEqual(self.client.post('/api/auth/departments/', {'name': 'Forbidden'}).status_code, 403)
        self.assertEqual(self.client.patch(f'/api/auth/departments/{own.pk}/', {'name': 'Forbidden'}).status_code, 403)

    def test_department_duplicates_and_invalid_translations_are_rejected(self):
        Department.objects.create(company=self.company, name='Sales')
        self.assertEqual(self.client.post('/api/auth/departments/', {'name': 'sales'}).status_code, 400)
        self.assertEqual(self.client.post('/api/auth/departments/', {
            'name': 'Bad translations', 'translations': {'ru': ['invalid']},
        }, format='json').status_code, 400)

    def test_defaults_preserve_existing_department_and_archive(self):
        from users.departments import seed_departments
        existing = Department.objects.create(company=self.company, name='VET', is_archived=True)
        seed_departments(Department, self.company.pk)
        seed_departments(Department, self.company.pk)
        self.assertEqual(Department.objects.filter(company=self.company).count(), 4)
        existing.refresh_from_db()
        self.assertEqual(existing.translations, {'ru': 'ВЭД', 'en': 'Foreign trade'})
        self.assertTrue(existing.is_archived)

    def test_invitation_cannot_create_department_from_free_text(self):
        response = self.client.post('/api/auth/invitations/', {
            'email': 'new@example.com', 'department_name': 'Unexpected department',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Department.objects.exists())

    def test_merge_legacy_wed_keeps_employee_and_invitation_links(self):
        from users.departments import merge_foreign_trade_departments
        legacy = Department.objects.create(company=self.company, name='WED')
        canonical = Department.objects.create(company=self.company, name='ВЭД')
        other_company = Company.objects.create(name='Independent departments')
        other = Department.objects.create(company=other_company, name='WED')
        membership = CompanyMembership.objects.create(user=self.admin, company=self.company, department=legacy)
        invitation = self.invite(department=legacy)
        self.admin.department_ref = legacy
        self.admin.department = legacy.name
        self.admin.save(update_fields=['department_ref', 'department'])
        self.assertEqual(merge_foreign_trade_departments(), 1)
        membership.refresh_from_db()
        invitation.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(membership.department_id, canonical.pk)
        self.assertEqual(invitation.department_id, canonical.pk)
        self.assertEqual(self.admin.department_ref_id, canonical.pk)
        self.assertEqual(self.admin.department, 'ВЭД')
        self.assertTrue(Department.objects.filter(pk=other.pk, company=other_company).exists())
        self.assertFalse(Department.objects.filter(pk=legacy.pk).exists())
        self.assertEqual(merge_foreign_trade_departments(), 0)

    def test_seed_recognises_legacy_wed(self):
        from users.departments import seed_departments
        existing = Department.objects.create(company=self.company, name='WED')
        seed_departments(Department, self.company.pk)
        self.assertEqual(Department.objects.filter(company=self.company).count(), 4)
        existing.refresh_from_db()
        self.assertEqual(existing.translations['ru'], 'ВЭД')
