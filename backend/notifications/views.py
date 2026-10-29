from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from groups.models import Membership

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # A notification is only ever visible to whoever must act on it: the
        # invitee for a group_invite, or the group's *current* admin for a
        # group_join_request (resolved dynamically, so it follows admin handoffs).
        user = self.request.user
        return Notification.objects.filter(
            Q(notification_type=Notification.Type.GROUP_INVITE, user=user)
            | Q(notification_type=Notification.Type.GROUP_JOIN_REQUEST, group__admin=user)
        ).select_related('group', 'group__admin', 'user')

    def _resolve(self, request, pk, new_status):
        notification = get_object_or_404(self.get_queryset(), pk=pk)
        if notification.status != Notification.Status.PENDING:
            raise ValidationError('This notification has already been resolved.')

        if new_status == Notification.Status.ACCEPTED:
            group, target_user = notification.group, notification.user
            # Re-validate at accept time -- group membership may have
            # changed since this notification was created (e.g. the user
            # already joined via the other pending notification type).
            if target_user.pk == group.admin_id or Membership.objects.filter(group=group, user=target_user).exists():
                raise ValidationError('This user is already a member of the group.')
            if group.parent_id is not None and not Membership.objects.filter(
                group_id=group.parent_id, user=target_user
            ).exists():
                raise ValidationError('This user must be a member of the parent group before joining this subgroup.')
            roles = notification.roles if notification.notification_type == Notification.Type.GROUP_INVITE else []
            Membership.objects.create(group=group, user=target_user, roles=roles)

        notification.status = new_status
        notification.save(update_fields=['status', 'modified_at'])
        return Response(NotificationSerializer(notification).data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        return self._resolve(request, pk, Notification.Status.ACCEPTED)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        return self._resolve(request, pk, Notification.Status.DECLINED)
