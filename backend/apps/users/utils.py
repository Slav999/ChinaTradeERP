from django.core.mail import send_mail
from django.conf import settings


def send_verification_email(email, code):
    subject = "Подтверждение Email"
    message = f"Ваш код подтверждения: {code}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
