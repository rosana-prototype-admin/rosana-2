from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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
            opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related('author').annotate(
            up_count=Count('votes', filter=Q(votes__value=1), distinct=True),
            down_count=Count('votes', filter=Q(votes__value=-1), distinct=True),
        ).prefetch_related(
            Prefetch('votes', queryset=CommentVote.objects.filter(author=self.request.user), to_attr='my_votes')
        )
        opportunity_pk = self.kwargs.get('opportunity_pk')
        if opportunity_pk is not None:
            queryset = queryset.filter(opportunity_id=opportunity_pk)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if 'opportunity_pk' in self.kwargs:
            context['opportunity'] = self.get_ancestor()
        return context

    def create(self, request, *args, **kwargs):
        if 'opportunity_pk' not in self.kwargs:
            raise ValidationError(
                'A Comment must be created via /opportunities/{opportunity_pk}/comments/.'
            )
        return super().create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft delete: preserves replies and the row itself (tombstoned by
        # CommentSerializer.to_representation), never a real DB delete.
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at', 'modified_at'])

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
