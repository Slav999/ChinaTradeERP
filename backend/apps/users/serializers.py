from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework.exceptions import APIException
from django.utils import timezone, translation
from django_countries import countries
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import hashlib
import random
import re

from .access import (
    access_role_account_flags,
    ensure_default_access_structure,
    user_permission_codes,
)
from .company_defaults import company_defaults_for_country
from .company_setup import ensure_default_company_directories
from .models import AccessRole, Company, CompanyMembership, Department, Invitation
from .utils import send_invitation_email, send_verification_email

User = get_user_model()

PASSWORD_PATTERN = re.compile(r'^(?=.*[A-Z])(?=.*\d).{8,}$')


def validate_password_strength(value):
    if not PASSWORD_PATTERN.match(value or ''):
        raise serializers.ValidationError(
            "Password must be at least 8 characters and include an uppercase letter and a number."
        )
    try:
        validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))


def generate_numeric_code():
    return str(random.randint(100000, 999999))


def hash_code(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


def code_matches(stored_value, raw_value):
    if not stored_value or not raw_value:
        return False
    return stored_value == raw_value or stored_value == hash_code(raw_value)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    company_name = serializers.CharField(write_only=True)
    business_country = serializers.ChoiceField(choices=countries, write_only=True)
    language_code = serializers.ChoiceField(choices=Company.LANGUAGE_CHOICES, write_only=True, default='ru')

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2', 'company_name', 'business_country', 'language_code')
        read_only_fields = ('id',)

    def validate_email(self, value):
        email = value.strip().lower()
        try:
            validate_email(email)
        except DjangoValidationError:
            raise serializers.ValidationError("Invalid email format.")
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Email is already in use.")
        return email

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        validate_password_strength(data['password'])

        company_name = data.get('company_name', '').strip()
        if not company_name:
            raise serializers.ValidationError("Company name is required.")

        if Company.objects.filter(name__iexact=company_name).exists():
            raise serializers.ValidationError(
                "Company \"%s\" already exists. Please ask your administrator to invite you."
                % company_name
            )

        if not data.get('business_country'):
            raise serializers.ValidationError("Country of business is required.")

        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        company_name = validated_data.pop('company_name').strip()
        business_country = validated_data.pop('business_country')
        language_code = validated_data.pop('language_code', 'ru')

        code = generate_numeric_code()
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role='admin',
            verification_code=hash_code(code),
            verification_code_expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        send_verification_email(user.email, code)

        company_defaults = company_defaults_for_country(business_country)
        company = Company(name=company_name, created_by=user, language_code=language_code)
        company.apply_country_defaults(company_defaults['business_country'])
        company.save()
        roles = ensure_default_access_structure(company)
        ensure_default_company_directories(company)

        user.company = company
        user.notification_language = language_code
        user.is_company_admin = True
        user.access_role = roles.get('Company admin')
        user.save(update_fields=['company', 'notification_language', 'is_company_admin', 'access_role'])
        CompanyMembership.objects.get_or_create(
            user=user,
            company=company,
            defaults={
                'role': 'admin',
                'access_role': user.access_role,
                'is_company_admin': True,
            },
        )
        from products.currency import refresh_company_rates
        from products.models import CompanySettings

        settings = CompanySettings.objects.create(
            company=company,
            **CompanySettings.default_values(company.business_country),
        )
        refresh_company_rates(company, settings)

        return user


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ('id', 'name', 'translations', 'is_archived')
        validators = []

    def validate_translations(self, value):
        if not isinstance(value, dict) or set(value) - {'ru', 'en'}:
            raise serializers.ValidationError('Use Russian and English names.')
        if any(not isinstance(name, str) or len(name.strip()) > 150 for name in value.values()):
            raise serializers.ValidationError('Department names must be at most 150 characters.')
        return {key: name.strip() for key, name in value.items()}

    def validate_name(self, value):
        value = value.strip()
        duplicates = Department.objects.filter(
            company=self.context['request'].user.company, name__iexact=value,
        )
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError('A department with this name already exists.')
        return value


class AccessRoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(many=True, read_only=True, slug_field='code')

    class Meta:
        model = AccessRole
        fields = ('id', 'name', 'description', 'permissions', 'is_system')


class CompanyMembershipSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    access_role_name = serializers.CharField(source='access_role.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_translations = serializers.JSONField(source='department.translations', read_only=True)

    class Meta:
        model = CompanyMembership
        fields = (
            'id', 'company', 'company_name', 'role', 'role_display',
            'access_role', 'access_role_name', 'department_name', 'department_translations',
            'position', 'is_company_admin', 'status', 'created_at',
            'disabled_at', 'disabled_by', 'disable_reason',
        )


class EmployeeMembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    middle_name = serializers.CharField(source='user.middle_name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    work_email = serializers.EmailField(source='user.work_email', read_only=True)
    personal_email = serializers.EmailField(source='user.personal_email', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    access_role_name = serializers.CharField(source='access_role.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_translations = serializers.JSONField(source='department.translations', read_only=True)
    disabled_by_email = serializers.EmailField(source='disabled_by.email', read_only=True)
    can_dismiss = serializers.SerializerMethodField()

    class Meta:
        model = CompanyMembership
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'middle_name',
            'phone', 'work_email', 'personal_email', 'role', 'role_display',
            'access_role', 'access_role_name', 'department_name', 'department_translations', 'position',
            'is_company_admin', 'status', 'created_at', 'disabled_at',
            'disabled_by_email', 'disable_reason', 'can_dismiss',
        )

    def get_can_dismiss(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if obj.status != CompanyMembership.STATUS_ACTIVE:
            return False
        if obj.user_id == request.user.id:
            return False
        if not request.user.is_company_admin:
            return False
        if obj.is_company_admin and obj.company.created_by_id != request.user.id:
            return False
        return True


class EmployeeAccessRoleUpdateSerializer(serializers.Serializer):
    access_role = serializers.PrimaryKeyRelatedField(queryset=AccessRole.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.company_id:
            ensure_default_access_structure(request.user.company)
            self.fields['access_role'].queryset = AccessRole.objects.filter(
                company=request.user.company,
            )

    def validate_access_role(self, access_role):
        request = self.context['request']
        if access_role.company_id != request.user.company_id:
            raise serializers.ValidationError('Access role is not available for your company.')
        return access_role


class SwitchCompanySerializer(serializers.Serializer):
    company_id = serializers.IntegerField()

    def validate_company_id(self, value):
        request = self.context['request']
        try:
            membership = CompanyMembership.objects.select_related(
                'company', 'department', 'access_role'
            ).get(user=request.user, company_id=value, status=CompanyMembership.STATUS_ACTIVE)
        except CompanyMembership.DoesNotExist:
            raise serializers.ValidationError("Company is not available for this account.")
        self.membership = membership
        return value

    def save(self):
        self.membership.apply_to_user()
        return self.membership


class InvitationDeliveryError(APIException):
    status_code = 503
    default_detail = 'Unable to send invitation email. Please try again.'
    default_code = 'invitation_delivery_failed'


class InvitationSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    department_display = serializers.CharField(source='department.name', read_only=True)
    department_translations = serializers.JSONField(source='department.translations', read_only=True)
    access_role_display = serializers.CharField(source='access_role.name', read_only=True)
    invited_by_display = serializers.CharField(source='invited_by.email', read_only=True)
    accept_url = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = (
            'id', 'email', 'first_name', 'last_name', 'position', 'role',
            'department', 'department_name', 'department_display', 'department_translations',
            'access_role', 'access_role_display', 'invited_by_display',
            'status', 'expires_at', 'accepted_at', 'created_at', 'accept_url',
        )
        read_only_fields = ('id', 'role', 'status', 'expires_at', 'accepted_at', 'created_at', 'accept_url')
        extra_kwargs = {
            'department': {'required': False, 'allow_null': True},
            'access_role': {'required': False, 'allow_null': True},
        }

    def get_accept_url(self, obj):
        token = getattr(obj, '_raw_token', None)
        if not token:
            return None
        request = self.context.get('request')
        frontend_url = request.headers.get('X-Frontend-Origin') if request else None
        frontend_url = frontend_url or 'http://localhost:5173'
        return f"{frontend_url.rstrip('/')}/accept-invite?token={token}"

    def validate_email(self, value):
        email = value.strip().lower()
        try:
            validate_email(email)
        except DjangoValidationError:
            raise serializers.ValidationError("Invalid email format.")
        return email

    def validate(self, data):
        request_user = self.context['request'].user
        if not request_user.is_company_admin:
            raise PermissionDenied("Only company admins can invite employees.")
        if not request_user.company_id:
            raise serializers.ValidationError("Your user is not linked to a company.")

        invited_user = User.objects.filter(email__iexact=data.get('email')).first()
        if invited_user and (
            invited_user.company_id == request_user.company_id
            or CompanyMembership.objects.filter(user=invited_user, company=request_user.company).exists()
        ):
            raise serializers.ValidationError("This employee is already linked to your company.")

        role = data.get('access_role')
        if role and role.company_id != request_user.company_id:
            raise serializers.ValidationError("Access role is not available for your company.")
        if not role:
            roles = ensure_default_access_structure(request_user.company)
            role = roles['Viewer']
            data['access_role'] = role
        if (
            role.name == 'Company admin'
            and request_user.company.created_by_id != request_user.id
        ):
            raise PermissionDenied('Only the company creator can grant company administrator access.')

        legacy_role, _is_company_admin = access_role_account_flags(role)
        data['role'] = legacy_role

        department = data.get('department')
        if data.get('department_name'):
            raise serializers.ValidationError({'department_name': 'Select a department from company settings.'})
        if department and (department.company_id != request_user.company_id or department.is_archived):
            raise serializers.ValidationError({'department': 'Department is not available for your company.'})

        return data

    @transaction.atomic
    def create(self, validated_data):
        request_user = self.context['request'].user
        # Serialise sends for one company, including duplicate invitations.
        Company.objects.select_for_update().get(pk=request_user.company_id)
        validated_data.pop('department_name', None)

        Invitation.objects.filter(
            company=request_user.company,
            email=validated_data['email'],
            status=Invitation.STATUS_PENDING,
        ).update(status=Invitation.STATUS_REVOKED)

        raw_token = Invitation.build_token()
        invitation = Invitation(
            **validated_data,
            company=request_user.company,
            invited_by=request_user,
            expires_at=timezone.now() + timezone.timedelta(days=Invitation.VALIDITY_DAYS),
        )
        invitation.set_token(raw_token)
        invitation.save()
        invitation._raw_token = raw_token
        try:
            send_invitation_email(invitation.email, raw_token, request_user.company.name)
        except Exception as exc:
            raise InvitationDeliveryError() from exc
        return invitation


class InvitationPreviewSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_display = serializers.CharField(source='department.name', read_only=True)
    department_translations = serializers.JSONField(source='department.translations', read_only=True)
    access_role_display = serializers.CharField(source='access_role.name', read_only=True)
    account_exists = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = (
            'email', 'first_name', 'last_name', 'position', 'role',
            'company_name', 'department_display', 'department_translations', 'access_role_display',
            'account_exists', 'expires_at',
        )

    def get_account_exists(self, obj):
        return User.objects.filter(email__iexact=obj.email).exists()


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()
    username = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password2 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, data):
        token_hash = Invitation.hash_token(data['token'])
        try:
            invitation = Invitation.objects.select_related(
                'company', 'department', 'access_role'
            ).get(token_hash=token_hash)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Invitation is invalid or expired.")

        invitation.mark_expired_if_needed()
        if invitation.status != Invitation.STATUS_PENDING:
            raise serializers.ValidationError("Invitation is invalid or expired.")

        request = self.context.get('request')
        existing_user = User.objects.filter(email__iexact=invitation.email).first()
        if existing_user:
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError("Please sign in to accept this invitation.")
            if request.user.email.lower() != invitation.email.lower():
                raise serializers.ValidationError("This invitation belongs to another email.")
            if CompanyMembership.objects.filter(user=request.user, company=invitation.company).exists():
                raise serializers.ValidationError("This account is already linked to this company.")
        else:
            if data.get('password') != data.get('password2'):
                raise serializers.ValidationError("Passwords do not match.")
            validate_password_strength(data.get('password'))

        data['invitation'] = invitation
        data['existing_user'] = existing_user
        return data

    @transaction.atomic
    def save(self):
        invitation = Invitation.objects.select_for_update().get(pk=self.validated_data['invitation'].pk)
        if invitation.status != Invitation.STATUS_PENDING or invitation.is_expired:
            raise serializers.ValidationError('Invitation is invalid or expired.')
        user = self.validated_data.get('existing_user')
        if not user:
            username = self.validated_data.get('username') or invitation.email.split('@')[0]
            first_name = self.validated_data.get('first_name') or invitation.first_name
            last_name = self.validated_data.get('last_name') or invitation.last_name

            user = User.objects.create_user(
                username=username,
                email=invitation.email,
                password=self.validated_data['password'],
                first_name=first_name,
                last_name=last_name,
                is_email_verified=True,
                notification_language=invitation.company.language_code or 'ru',
            )

        legacy_role, is_company_admin = access_role_account_flags(invitation.access_role)
        membership, _ = CompanyMembership.objects.get_or_create(
            user=user,
            company=invitation.company,
            defaults={
                'role': legacy_role,
                'department': invitation.department,
                'access_role': invitation.access_role,
                'position': invitation.position,
                'is_company_admin': is_company_admin,
            },
        )
        membership.apply_to_user()

        invitation.status = Invitation.STATUS_ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['status', 'accepted_at'])
        return user


class InviteUserSerializer(InvitationSerializer):
    username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password2 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta(InvitationSerializer.Meta):
        fields = InvitationSerializer.Meta.fields + ('username', 'password', 'password2')

    def validate(self, data):
        data.pop('username', None)
        data.pop('password', None)
        data.pop('password2', None)
        return super().validate(data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        token['company_id'] = user.company_id
        token['access_role_id'] = user.access_role_id
        return token

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(email=email, password=password)
        if not user:
            raise AuthenticationFailed("Invalid email or password.")
        if not user.is_email_verified:
            raise AuthenticationFailed("Email is not verified.")
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_business_country = serializers.SerializerMethodField()
    company_logo_url = serializers.SerializerMethodField()
    company_business_country_name = serializers.SerializerMethodField()
    company_currency_code = serializers.CharField(source='company.base_currency_code', read_only=True)
    company_currency_symbol = serializers.CharField(source='company.base_currency_symbol', read_only=True)
    company_language_code = serializers.CharField(source='company.language_code', read_only=True)
    company_settings_needs_review = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    access_role_name = serializers.CharField(source='access_role.name', read_only=True)
    department_ref_name = serializers.CharField(source='department_ref.name', read_only=True)
    memberships = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'role', 'role_display', 'company_id', 'company_name',
            'company_business_country', 'company_business_country_name',
            'company_logo_url',
            'company_currency_code', 'company_currency_symbol', 'company_settings_needs_review',
            'company_language_code',
            'is_company_admin', 'access_role', 'access_role_name', 'department_ref',
            'department_ref_name', 'first_name', 'last_name', 'middle_name', 'phone',
            'work_email', 'personal_email', 'position', 'department',
            'birth_date', 'hire_date', 'notification_language', 'avatar', 'memberships',
            'permissions',
        )
        read_only_fields = (
            'id', 'username', 'email', 'role', 'role_display', 'company_id', 'company_name',
            'company_business_country', 'company_business_country_name',
            'company_currency_code', 'company_currency_symbol', 'company_settings_needs_review',
            'company_language_code',
            'is_company_admin', 'access_role', 'access_role_name', 'department_ref',
            'department_ref_name', 'memberships', 'permissions',
        )

    def get_permissions(self, obj):
        return sorted(user_permission_codes(obj))

    def get_company_logo_url(self, obj):
        if not obj.company_id or not obj.company.logo:
            return ''
        url = obj.company.logo.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_memberships(self, obj):
        memberships = obj.company_memberships.select_related(
            'company', 'department', 'access_role'
        ).filter(status=CompanyMembership.STATUS_ACTIVE)
        return CompanyMembershipSerializer(memberships, many=True).data

    def get_company_business_country(self, obj):
        return str(obj.company.business_country) if obj.company_id else ''

    def get_company_business_country_name(self, obj):
        if not obj.company_id or not obj.company.business_country:
            return ''
        request = self.context.get('request')
        requested_language = getattr(getattr(request, 'user', None), 'notification_language', None)
        language = 'en' if requested_language == 'en' else 'ru'
        with translation.override(language):
            return str(obj.company.business_country.name)

    def get_company_settings_needs_review(self, obj):
        if not obj.company_id or not obj.is_company_admin:
            return False
        try:
            company_settings = obj.company.product_settings
        except Exception:
            return True
        return company_settings.settings_confirmed_at is None
