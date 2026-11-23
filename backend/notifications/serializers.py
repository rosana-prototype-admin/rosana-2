from rest_framework import serializers

from accounts.serializers import UserSearchResultSerializer

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSearchResultSerializer(read_only=True)
    group = serializers.SerializerMethodField()
    organizational_roles = serializers.ListField(source='roles', read_only=True)
    is_requester = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'status', 'group', 'user', 'rosana_role', 'organizational_roles', 'permissions', 'is_requester', 'created_at', 'modified_at']
        read_only_fields = fields

    def get_group(self, obj):
        return {'id': obj.group_id, 'name': obj.group.name}

    def get_is_requester(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.notification_type == Notification.Type.GROUP_JOIN_REQUEST and obj.user_id == request.user.pk)
