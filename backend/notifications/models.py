from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A pending, accept/decline-able request tied to a Group."""

    class Type(models.TextChoices):
        GROUP_INVITE = 'group_invite', 'Group Invite'
        GROUP_JOIN_REQUEST = 'group_join_request', 'Group Join Request'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'

    notification_type = models.CharField(max_length=32, choices=Type.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, related_name='notifications')
    # The invitee (GROUP_INVITE) or the requester (GROUP_JOIN_REQUEST) -- the
    # one human whose membership is at stake.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_notifications'
    )
    roles = models.JSONField(default=list, blank=True)  # only meaningful for GROUP_INVITE; applied on accept
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'user', 'notification_type'],
                condition=models.Q(status='pending'),
                name='unique_pending_group_notification',
            ),
        ]

    def __str__(self):
        return f'{self.notification_type} for {self.user_id} on {self.group_id} ({self.status})'
