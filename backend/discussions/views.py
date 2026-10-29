from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from projects.models import Opportunity

from .models import Comment, CommentVote
from .permissions import CommentAccessPermission, CommentAncestorScopedMixin
from .serializers import CommentSerializer


class CommentViewSet(CommentAncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, CommentAccessPermission]

    def get_queryset(self):
        queryset = Comment.objects.filter(
            project__opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related('author').annotate(
            up_count=Count('votes', filter=Q(votes__value=1), distinct=True),
            down_count=Count('votes', filter=Q(votes__value=-1), distinct=True),
        ).prefetch_related(
            Prefetch('votes', queryset=CommentVote.objects.filter(author=self.request.user), to_attr='my_votes')
        )
        project_pk = self.kwargs.get('project_pk')
        if project_pk is not None:
            queryset = queryset.filter(project_id=project_pk)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if 'project_pk' in self.kwargs:
            context['project'] = self.get_ancestor()
        return context

    def create(self, request, *args, **kwargs):
        if 'project_pk' not in self.kwargs:
            raise ValidationError(
                'A Comment must be created via /projects/{project_pk}/comments/.'
            )
        return super().create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft delete: preserves replies and the row itself (tombstoned by
        # CommentSerializer.to_representation), never a real DB delete. Only
        # reachable here if CommentAccessPermission already confirmed the
        # requester is the author or the Opportunity owner (see its
        # has_object_permission) -- an owner deleting someone else's comment
        # is a moderator removal; an owner deleting their own is not.
        instance.deleted_at = timezone.now()
        instance.removed_by_moderator = self.request.user.pk != instance.author_id
        instance.save(update_fields=['deleted_at', 'removed_by_moderator', 'modified_at'])

    @action(detail=True, methods=['post'], url_path='delete-tree')
    def delete_tree(self, request, pk=None):
        # Stricter than CommentAccessPermission's destroy bar (author OR
        # manager) -- deleting a whole subtree necessarily also deletes any
        # replies from *other* users under it, so this is manager-only,
        # fetched explicitly the same way ProjectViewSet.comments_enabled
        # does for its own stricter-than-default bar.
        comment = get_object_or_404(self.get_queryset(), pk=pk)
        opportunity = comment.get_opportunity()
        if opportunity.manager_id != request.user.pk:
            raise PermissionDenied('Only the opportunity manager can delete a comment thread.')

        ids = comment.descendant_ids()
        Comment.objects.filter(pk__in=ids, deleted_at__isnull=True).update(
            deleted_at=timezone.now(), removed_by_moderator=True, modified_at=timezone.now()
        )

        refreshed = self.get_queryset().filter(pk__in=ids)
        return Response(CommentSerializer(refreshed, many=True, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        comment = self.get_object()
        try:
            value = int(request.data.get('value'))
        except (TypeError, ValueError):
            value = None
        if value not in (1, -1):
            raise ValidationError({'value': 'value must be 1 (up) or -1 (down).'})

        existing = CommentVote.objects.filter(comment=comment, author=request.user).first()
        if existing and existing.value == value:
            existing.delete()
        else:
            CommentVote.objects.update_or_create(
                comment=comment, author=request.user, defaults={'value': value}
            )

        refreshed = self.get_queryset().get(pk=comment.pk)
        return Response(CommentSerializer(refreshed, context=self.get_serializer_context()).data)
