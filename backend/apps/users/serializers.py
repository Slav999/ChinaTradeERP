from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Company
from .utils import send_verification_email
import random

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    company_name = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2', 'company_name')
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
        # пароль
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        if len(data['password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")

        # название компании обязательно
        company_name = data.get('company_name', '').strip()
        if not company_name:
            raise serializers.ValidationError("Company name is required.")

        # если компания с таким именем уже есть — регистрация публичная на неё
        # запрещена, для этого приглашает админ через /invite/
        if Company.objects.filter(name__iexact=company_name).exists():
            raise serializers.ValidationError(
                "Company “%s” already exists. Please ask your administrator to invite you."
                % company_name
            )

        return data

    def create(self, validated_data):
        # убираем лишние поля
        validated_data.pop('password2')
        company_name = validated_data.pop('company_name').strip()

        # создаём пользователя — сразу с ролью admin и кодом подтверждения
        code = str(random.randint(100000, 999999))
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role='admin',
            verification_code=code
        )
        send_verification_email(user.email, code)

        # создаём компанию именно под этого юзера
        company = Company.objects.create(name=company_name, created_by=user)

        user.company = company
        user.is_company_admin = True
        user.save()

        return user


class InviteUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'password', 'password2')
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
        if len(data['password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        request_user = self.context['request'].user
        if not request_user.is_company_admin:
            raise PermissionDenied("Only company admins can invite new users.")

        code = str(random.randint(100000, 999999))
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'viewer'),
            verification_code=code,
            company=request_user.company
        )
        send_verification_email(user.email, code)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        token['company_id'] = user.company_id
        return token

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(email=email, password=password)
        if not user:
            raise AuthenticationFailed("Неверный email или пароль.")
        if not user.is_email_verified:
            raise AuthenticationFailed("Email не подтверждён.")
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'company_id')
