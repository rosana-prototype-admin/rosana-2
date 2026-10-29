from rest_framework import serializers

from accounts.serializers import UserSearchResultSerializer

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.all(), required=False, allow_null=True
    )
    author = UserSearchResultSerializer(read_only=True)
    up_count = serializers.IntegerField(read_only=True)
    down_count = serializers.IntegerField(read_only=True)
    my_vote = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'project',
            'parent',
            'author',
            'body',
            'depth',
            'deleted_at',
            'up_count',
            'down_count',
            'my_vote',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'project', 'depth', 'deleted_at', 'created_at', 'modified_at']

    def get_my_vote(self, obj):
        votes = getattr(obj, 'my_votes', None)
        return votes[0].value if votes else None

    def validate_body(self, value):
        if self.instance and self.instance.deleted_at:
            raise serializers.ValidationError('This comment has been deleted and cannot be edited.')
        if not value.strip():
            raise serializers.ValidationError('Comment cannot be empty.')
        return value

    def validate(self, attrs):
        parent = attrs.get('parent')
        project = self.context.get('project') or getattr(self.instance, 'project', None)
        if parent is not None:
            if project and parent.project_id != project.pk:
                raise serializers.ValidationError(
                    {'parent': "Parent comment does not belong to this project."}
                )
            depth = parent.depth + 1
            if depth > Comment.MAX_DEPTH:
                raise serializers.ValidationError(
                    {'parent': f'Maximum reply depth ({Comment.MAX_DEPTH}) exceeded.'}
                )
            attrs['depth'] = depth
        else:
            attrs['depth'] = 0
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.deleted_at:
            data['author'] = None
            # The underlying body is preserved in the DB either way; only the
            # API representation is tombstoned, so moderator removals get a
            # distinct message instead of the generic blank-out.
            data['body'] = '[Comment removed by moderator]' if instance.removed_by_moderator else None
        return data
