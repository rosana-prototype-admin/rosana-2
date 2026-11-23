from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSearchResultSerializer
from geo.models import Jcode
from geo.serializers import JcodeSerializer
from notifications.models import Notification

from .models import Group, Membership, RosanaRole, group_creates_cycle
from .permissions import GROUP_PERMISSION_CODES, default_group_permissions, normalize_group_permissions


class GroupSerializer(serializers.ModelSerializer):
    admin = UserSearchResultSerializer(read_only=True)
    members = serializers.SerializerMethodField()  # effective (transitive) members
    jcodes = JcodeSerializer(many=True, read_only=True)  # admin-managed group jurisdiction assignments
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'parent', 'admin', 'user_role', 'members', 'jcodes', 'created_at', 'modified_at', 'archived_at', 'archived_by']
        # admin is fully read-only here -- only ever set by GroupViewSet.perform_create
        # (on the initial group) or the set-admin action (on reassignment), never a plain PATCH body.
        read_only_fields = ['id', 'admin', 'members', 'jcodes', 'created_at', 'modified_at', 'archived_at', 'archived_by']

    def get_members(self, obj):
        return UserSearchResultSerializer(obj.effective_members(), many=True).data

    def get_user_role(self, obj):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return None
        if obj.admin_id == request.user.pk:
            return 'admin'
        if obj.memberships.filter(user_id=request.user.pk).exists():
            return 'member'
        return None

    def validate(self, attrs):
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        if self.instance is not None and 'parent' in attrs and attrs['parent'] != self.instance.parent:
            if self.context['request'].user.pk != self.instance.admin_id:
                raise serializers.ValidationError({'parent': 'Only the group administrator can change the parent group.'})
        if self.instance is not None and parent is not None:
            if group_creates_cycle(self.instance.pk, parent):
                raise serializers.ValidationError({'parent': 'A group cannot be its own ancestor.'})
            # Reparenting under a different group requires being that new
            # parent's admin too -- otherwise "only the parent's admin can
            # create children" is trivially bypassed by creating a group
            # elsewhere and reparenting it in.
            if parent != self.instance.parent and parent.admin_id != self.context['request'].user.pk:
                raise serializers.ValidationError({'parent': 'You must be the admin of the new parent group.'})
        return attrs


class MembershipSerializer(serializers.ModelSerializer):
    """Used only for PATCH .../members/{user_id}/ (role edits) -- Membership
    rows are otherwise only ever created by NotificationViewSet.accept, once
    an invite or join request is approved."""

    user = UserSearchResultSerializer(read_only=True)
    group = serializers.PrimaryKeyRelatedField(read_only=True)
    organizational_roles = serializers.ListField(source='roles', default=list)
    permissions = serializers.JSONField(default=default_group_permissions)

    class Meta:
        model = Membership
        fields = ['id', 'group', 'user', 'rosana_role', 'organizational_roles', 'permissions', 'created_at', 'modified_at']
        read_only_fields = ['id', 'group', 'user', 'created_at', 'modified_at']

    def validate_organizational_roles(self, value):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError('organizational_roles must be a list of strings.')
        return value

    def validate_permissions(self, value):
        try:
            return normalize_group_permissions(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


def _validate_new_group_member(group, user):
    """Shared by GroupInviteSerializer and GroupJoinRequestSerializer: the
    checks that must hold before a Notification proposing `user` join `group`
    is allowed to be created."""
    if user.pk == group.admin_id:
        raise serializers.ValidationError('This user is already the group admin.')
    if Membership.objects.filter(group=group, user=user).exists():
        raise serializers.ValidationError('This user is already a member of this group.')
    if group.parent_id is not None and not Membership.objects.filter(group_id=group.parent_id, user=user).exists():
        raise serializers.ValidationError(
            'This user must already be a member of the parent group before joining a subgroup.'
        )


class GroupInviteSerializer(serializers.Serializer):
    """An admin proposing that `user_id` join their group -- creates a
    pending GROUP_INVITE Notification rather than adding the member directly."""

    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    organizational_roles = serializers.ListField(source='roles', default=list)
    permissions = serializers.JSONField(default=default_group_permissions)

    def validate_organizational_roles(self, value):
        # A bare ListField (no `child`) skips per-item coercion, so this
        # actually rejects non-string items instead of silently stringifying
        # them the way ListField(child=CharField()) would.
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError('organizational_roles must be a list of strings.')
        return value

    def validate_permissions(self, value):
        try:
            return normalize_group_permissions(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate(self, attrs):
        group = self.context['group']
        user = attrs['user']
        _validate_new_group_member(group, user)
        if Notification.objects.filter(
            group=group, user=user, notification_type=Notification.Type.GROUP_INVITE,
            status=Notification.Status.PENDING,
        ).exists():
            raise serializers.ValidationError('An invitation to this user is already pending.')
        return attrs

    def save(self):
        return Notification.objects.create(
            group=self.context['group'],
            user=self.validated_data['user'],
            notification_type=Notification.Type.GROUP_INVITE,
            roles=self.validated_data['roles'],
            permissions=self.validated_data['permissions'],
        )


class GroupJoinRequestSerializer(serializers.Serializer):
    """A user asking to join a group -- creates a pending GROUP_JOIN_REQUEST
    Notification addressed to the group's admin."""

    def validate(self, attrs):
        group = self.context['group']
        user = self.context['user']
        _validate_new_group_member(group, user)
        if Notification.objects.filter(
            group=group, user=user, notification_type=Notification.Type.GROUP_JOIN_REQUEST,
            status=Notification.Status.PENDING,
        ).exists():
            raise serializers.ValidationError('You already have a pending request to join this group.')
        return attrs

    def save(self):
        return Notification.objects.create(
            group=self.context['group'],
            user=self.context['user'],
            notification_type=Notification.Type.GROUP_JOIN_REQUEST,
        )


class GroupMemberSerializer(serializers.Serializer):
    """A flattened, read-only view of one Group member (admin or regular member)."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    group_admin_status = serializers.ChoiceField(choices=['admin', 'member'])
    rosana_role = serializers.ChoiceField(choices=RosanaRole.choices)
    organizational_roles = serializers.ListField(child=serializers.CharField(), default=list)
    permissions = serializers.JSONField()
    permissions_locked = serializers.BooleanField(default=False)


class GroupPermissionDefinitionSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=GROUP_PERMISSION_CODES)
    label = serializers.CharField()
    category = serializers.CharField()


class SetAdminSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())


class GroupJcodeUpdateSerializer(serializers.Serializer):
    jcode_ids = serializers.PrimaryKeyRelatedField(
        queryset=Jcode.objects.all(), many=True, allow_empty=True,
    )
