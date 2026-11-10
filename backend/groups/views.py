from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from notifications.serializers import NotificationSerializer
from accounts.audit import record_admin_event

from .models import Group, Membership
from .permissions import GroupAccessPermission
from .serializers import (
    GroupInviteSerializer,
    GroupJcodeUpdateSerializer,
    GroupJoinRequestSerializer,
    GroupMemberSerializer,
    GroupSerializer,
    MembershipSerializer,
    SetAdminSerializer,
)


def _group_members(group):
    """Flatten the admin (synthetic, no Membership row required) + direct members into one role-tagged list."""
    def _entry(user, role, roles=None):
        return {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': role,
            'roles': roles or [],
        }

    members = [_entry(group.admin, 'admin')]
    members += [_entry(membership.user, 'member', membership.roles) for membership in group.memberships.select_related('user')]
    return members


class GroupViewSet(viewsets.ModelViewSet):
    """Any authenticated user may read; only a group's admin may write to it (see GroupAccessPermission)."""

    queryset = Group.objects.select_related('parent', 'admin').prefetch_related('jcodes__country_code')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, GroupAccessPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        include_archived = self.request.query_params.get('include_archived') == 'true'
        if not include_archived or not (self.request.user.is_staff and self.request.user.is_active):
            queryset = queryset.filter(archived_at__isnull=True)
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        if request.user.is_staff and request.user.is_active:
            queryset = self.get_queryset()
        else:
            queryset = self.get_queryset().filter(
                Q(admin_id=request.user.pk) | Q(memberships__user_id=request.user.pk),
            ).distinct()
        return Response(self.get_serializer(queryset, many=True).data)

    def destroy(self, request, *args, **kwargs):
        """Keep DELETE as a backwards-compatible archive operation."""
        group = self.get_object()
        now = timezone.now()
        group_ids = group.descendant_group_ids()
        Group.objects.filter(pk__in=group_ids, archived_at__isnull=True).update(
            archived_at=now,
            archived_by=request.user,
        )
        record_admin_event(request, 'group.archived', group, after={'archived_at': now.isoformat()})
        return Response(status=204)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        if not request.user.is_staff or not request.user.is_active:
            return Response({'detail': 'Only platform administrators can restore archived groups.'}, status=403)
        group = get_object_or_404(Group.objects.all(), pk=pk)
        group_ids = group.descendant_group_ids()
        Group.objects.filter(pk__in=group_ids).update(archived_at=None, archived_by=None)
        record_admin_event(request, 'group.restored', group, after={'archived_at': None})
        return Response(self.get_serializer(group).data)

    def perform_create(self, serializer):
        parent = serializer.validated_data.get('parent')
        if parent is not None and parent.admin_id != self.request.user.pk:
            raise PermissionDenied("You must be the parent group's admin to create a subgroup.")
        serializer.save(admin=self.request.user)

    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        # Any authenticated user may read (GroupAccessPermission allows GET
        # through for everyone) -- adding a member is no longer a direct
        # write here, see `invite` below.
        group = self.get_object()
        return Response(GroupMemberSerializer(_group_members(group), many=True).data)

    @action(detail=True, methods=['post'], url_path='invite')
    def invite(self, request, pk=None):
        # Admin-only (POST is non-safe) via GroupAccessPermission. Creates a
        # pending invite Notification instead of adding the member directly.
        group = self.get_object()
        serializer = GroupInviteSerializer(data=request.data, context={'group': group})
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()
        return Response(NotificationSerializer(notification).data, status=201)

    @action(detail=True, methods=['post'], url_path='request-to-join')
    def request_to_join(self, request, pk=None):
        # Any authenticated user may request to join any group -- looser than
        # GroupAccessPermission's default write gate, so fetch the group
        # directly rather than via self.get_object() to bypass the admin-only
        # object-level check for this specific action.
        group = get_object_or_404(Group.objects.all(), pk=pk)
        serializer = GroupJoinRequestSerializer(data={}, context={'group': group, 'user': request.user})
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()
        return Response(NotificationSerializer(notification).data, status=201)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'members/(?P<user_id>\d+)')
    def member_detail(self, request, pk=None, user_id=None):
        group = self.get_object()  # admin-only (PATCH/DELETE are both non-safe)
        membership = get_object_or_404(Membership, group=group, user_id=user_id)

        if request.method == 'DELETE':
            membership.delete()
            return Response(status=204)

        serializer = MembershipSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(GroupMemberSerializer(_group_members(group), many=True).data)

    @action(detail=True, methods=['post'], url_path='set-admin')
    def set_admin(self, request, pk=None):
        group = self.get_object()  # admin-only (POST is non-safe)
        serializer = SetAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_admin = serializer.validated_data['user_id']

        membership = get_object_or_404(Membership, group=group, user=new_admin)
        previous_admin = group.admin
        if new_admin.pk == previous_admin.pk:
            raise ValidationError({'user_id': 'This user is already the group administrator.'})
        if not new_admin.is_active:
            raise ValidationError({'user_id': 'The new administrator must have an active account.'})
        if not new_admin.email_verified:
            raise ValidationError({'user_id': 'The new administrator must have a verified email address.'})

        # Keep the role swap atomic: either both users' access and the admin
        # pointer change, or none of them do.
        with transaction.atomic():
            membership.delete()
            group.admin = new_admin
            group.save(update_fields=['admin', 'modified_at'])
            # The outgoing admin keeps access as a regular member.
            Membership.objects.get_or_create(group=group, user=previous_admin, defaults={'roles': []})

        record_admin_event(
            request,
            'group.admin_transferred',
            group,
            before={'admin_id': previous_admin.pk, 'admin_username': previous_admin.username},
            after={'admin_id': new_admin.pk, 'admin_username': new_admin.username},
            group=group,
        )

        return Response(GroupSerializer(group, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['patch'], url_path='jcodes')
    def update_jcodes(self, request, pk=None):
        group = self.get_object()  # admin-only (PATCH is non-safe)
        serializer = GroupJcodeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group.jcodes.set(serializer.validated_data['jcode_ids'])
        group.save(update_fields=['modified_at'])
        return Response(self.get_serializer(group).data)
