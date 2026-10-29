from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from notifications.serializers import NotificationSerializer

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
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        queryset = self.get_queryset().filter(
            Q(admin_id=request.user.pk) | Q(memberships__user_id=request.user.pk),
        ).distinct()
        return Response(self.get_serializer(queryset, many=True).data)

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
        membership.delete()
        group.admin = new_admin
        group.save(update_fields=['admin', 'modified_at'])
        # The outgoing admin keeps access to the group as a regular member,
        # rather than disappearing from it entirely.
        Membership.objects.get_or_create(group=group, user=previous_admin, defaults={'roles': []})

        return Response(GroupSerializer(group, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['patch'], url_path='jcodes')
    def update_jcodes(self, request, pk=None):
        group = self.get_object()  # admin-only (PATCH is non-safe)
        serializer = GroupJcodeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group.jcodes.set(serializer.validated_data['jcode_ids'])
        group.save(update_fields=['modified_at'])
        return Response(self.get_serializer(group).data)
