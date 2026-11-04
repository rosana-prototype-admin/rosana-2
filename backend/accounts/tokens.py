from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Generate a token that becomes invalid as soon as the email is verified."""

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{user.password}{timestamp}{user.email}{user.email_verified}'


email_verification_token = EmailVerificationTokenGenerator()
