from rest_framework import serializers

from accounts.serializers import UserSearchResultSerializer

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSearchResultSerializer(read_only=True)
    group = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'status', 'group', 'user', 'roles', 'created_at', 'modified_at']
        read_only_fields = fields

    def get_group(self, obj):
        return {'id': obj.group_id, 'name': obj.group.name}
