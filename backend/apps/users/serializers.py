from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .utils import send_verification_email
import random

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2', 'role')
        read_only_fields = ('id', 'role')

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Пароли не совпадают.")
        if len(data['password']) < 8:
            raise serializers.ValidationError("Пароль должен быть не менее 8 символов.")
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        code = str(random.randint(100000, 999999))
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password'],
            role='admin',
            verification_code=code
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
        return token

    def validate(self, attrs):
        # логиним по email + password
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(email=email, password=password)
        if not user:
            raise AuthenticationFailed("Неверный email или пароль.")
        if not user.is_email_verified:
            raise AuthenticationFailed("Email не подтверждён.")

        data = super().validate(attrs)
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role')
