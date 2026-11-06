from .models import Invitation

from django.conf import settings
from django.core.mail import send_mail


def send_verification_email(email, code):
    subject = "Email verification"
    message = f"Your verification code: {code}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


def send_invitation_email(email, token, company_name):
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    invite_url = f"{frontend_url.rstrip('/')}/accept-invite?token={token}"
    subject = f"Invitation to {company_name}"
    message = (
        f"You have been invited to join {company_name}.\n\n"
        f"Open this link to accept the invitation:\n{invite_url}\n\n"
        f"The invitation expires in {Invitation.VALIDITY_DAYS} days."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
