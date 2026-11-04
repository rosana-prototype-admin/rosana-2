from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def verification_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    query = urlencode({'uid': uid, 'token': email_verification_token.make_token(user)})
    return f'{settings.FRONTEND_BASE_URL.rstrip("/")}/verify-email?{query}'


def send_verification_email(user):
    url = verification_url(user)
    send_mail(
        'Verify your Rosana email address',
        (
            f'Hello {user.first_name or user.username},\n\n'
            'Please verify your email address to activate your Rosana account:\n\n'
            f'{url}\n\n'
            'If you did not create this account, you can ignore this email.'
        ),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
