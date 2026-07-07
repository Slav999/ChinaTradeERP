from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.crypto import get_random_string
from django.utils import timezone
import hashlib
import secrets

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='companies_created'
    )

    def __str__(self):
        return self.name


class Department(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='departments'
    )
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'name')
        ordering = ('name',)

    def __str__(self):
        return f"{self.name} ({self.company})"


class AccessPermission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ('code',)

    def __str__(self):
        return self.name


class AccessRole(models.Model):
    company = models.ForeignKey(
        Company,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='access_roles'
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(AccessPermission, blank=True, related_name='roles')
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'name')
        ordering = ('name',)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('viewer', 'Viewer'),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    is_email_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=64, blank=True, null=True)
    verification_code_expires_at = models.DateTimeField(null=True, blank=True)
    reset_code = models.CharField(max_length=64, blank=True)
    reset_code_expires_at = models.DateTimeField(null=True, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    work_email = models.EmailField(blank=True)
    personal_email = models.EmailField(blank=True)
    position = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)
    department_ref = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='employees'
    )
    access_role = models.ForeignKey(
        AccessRole,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='employees'
    )
    birth_date = models.DateField(null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    notification_language = models.CharField(max_length=20, default='ru', blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    company = models.ForeignKey(
        Company,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='users'
    )
    is_company_admin = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"


class CompanyMembership(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_INVITED = 'invited'
    STATUS_DISABLED = 'disabled'

    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INVITED, 'Invited'),
        (STATUS_DISABLED, 'Disabled'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_memberships'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(max_length=20, choices=CustomUser.ROLE_CHOICES, default='viewer')
    department = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='memberships'
    )
    access_role = models.ForeignKey(
        AccessRole,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='memberships'
    )
    position = models.CharField(max_length=150, blank=True)
    is_company_admin = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    disabled_at = models.DateTimeField(null=True, blank=True)
    disabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='disabled_company_memberships'
    )
    disable_reason = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'company')
        ordering = ('company__name',)

    def apply_to_user(self):
        self.user.company = self.company
        self.user.role = self.role
        self.user.department_ref = self.department
        self.user.department = self.department.name if self.department else ''
        self.user.access_role = self.access_role
        self.user.position = self.position
        self.user.is_company_admin = self.is_company_admin
        self.user.save(update_fields=[
            'company', 'role', 'department_ref', 'department',
            'access_role', 'position', 'is_company_admin',
        ])

    def __str__(self):
        return f"{self.user.email} @ {self.company}"


class Invitation(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REVOKED = 'revoked'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REVOKED, 'Revoked'),
        (STATUS_EXPIRED, 'Expired'),
    )

    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    position = models.CharField(max_length=150, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='sent_invitations'
    )
    role = models.CharField(max_length=20, choices=CustomUser.ROLE_CHOICES, default='viewer')
    department = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invitations'
    )
    access_role = models.ForeignKey(
        AccessRole,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='invitations'
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['company', 'email', 'status']),
            models.Index(fields=['token_hash']),
        ]

    @staticmethod
    def hash_token(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @classmethod
    def build_token(cls):
        return secrets.token_urlsafe(32)

    def set_token(self, token):
        self.token_hash = self.hash_token(token)

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    def mark_expired_if_needed(self):
        if self.status == self.STATUS_PENDING and self.is_expired:
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=['status'])

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        if not self.token_hash:
            self.token_hash = self.hash_token(get_random_string(48))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} -> {self.company}"
