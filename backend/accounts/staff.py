from django.core.exceptions import ValidationError

from .models import User


def validate_staff_account_change(user, *, is_active=None, is_staff=None):
    """Prevent an account change from removing the last active staff user."""

    current_active_staff = user.is_active and user.is_staff
    future_active_staff = (
        user.is_active if is_active is None else is_active
    ) and (
        user.is_staff if is_staff is None else is_staff
    )
    if not current_active_staff or future_active_staff:
        return

    has_another_active_staff = User.objects.filter(
        is_active=True,
        is_staff=True,
    ).exclude(pk=user.pk).exists()
    if not has_another_active_staff:
        raise ValidationError('At least one active platform administrator must remain.')
