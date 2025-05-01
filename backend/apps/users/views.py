from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
import random
import time

from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        try:
            user = User.objects.get(email=email)
            if user.verification_code == code:
                user.is_email_verified = True
                user.verification_code = ""
                user.save()
                return Response({"message": "Email подтверждён"}, status=200)
            return Response({"error": "Неверный код"}, status=400)
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        key = f"forgot_password:{ip}"
        attempts = cache.get(key, 0)

        if attempts >= 5:
            return Response({"detail": "Слишком много попыток. Подождите."}, status=429)

        cache.set(key, attempts + 1, timeout=60)

        email = request.data.get('email')
        if not email:
            return Response({"detail": "Email обязателен."}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден."}, status=404)

        code = str(random.randint(100000, 999999))
        user.reset_code = code
        user.save()

        send_mail(
            subject='Код для сброса пароля',
            message=f'Ваш код: {code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return Response({"detail": "Код отправлен на email."})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        key = f"reset_password:{ip}"
        attempts = cache.get(key, 0)

        if attempts >= 5:
            return Response({"detail": "Слишком много попыток. Подождите."}, status=429)

        cache.set(key, attempts + 1, timeout=60)

        email = request.data.get('email')
        code = request.data.get('code')
        new_password = request.data.get('new_password')

        if not all([email, code, new_password]):
            return Response({"detail": "Все поля обязательны."}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден."}, status=404)

        if user.reset_code != code:
            return Response({"detail": "Неверный код."}, status=400)

        user.set_password(new_password)
        user.reset_code = ''
        user.save()

        return Response({"detail": "Пароль обновлён."}, status=200)