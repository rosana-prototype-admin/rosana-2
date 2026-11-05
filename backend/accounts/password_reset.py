import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def password_reset_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    query = urlencode({'uid': uid, 'token': default_token_generator.make_token(user)})
    return f'{settings.FRONTEND_BASE_URL.rstrip("/")}/reset-password?{query}'


def send_password_reset_email(user):
    try:
        send_mail(
            'Reset your Rosana password',
            (
                f'Hello {user.first_name or user.username},\n\n'
                'We received a request to reset your Rosana password. Use this link '
                f'to choose a new password:\n\n{password_reset_url(user)}\n\n'
                'This link expires after a limited time. If you did not request a '
                'password reset, you can ignore this email.'
            ),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
    except Exception:
        logger.exception('Unable to send password reset email', extra={'user_id': user.pk})
