from django.conf import settings
from django.db import models


class Comment(models.Model):
    """A threaded comment on a Project, with replies capped at MAX_DEPTH."""

    MAX_DEPTH = 3  # root = depth 0, deepest reply = depth 3

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='comments',
    )
    # ~300 words / one page of 12pt text, at ~6.5 characters per word average.
    body = models.TextField(max_length=2000)
    depth = models.PositiveSmallIntegerField(default=0)
    deleted_at = models.DateTimeField(null=True, blank=True)
    removed_by_moderator = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['project', 'parent']),
            models.Index(fields=['project', 'created_at']),
        ]

    def __str__(self):
        return f'Comment {self.pk} on Project {self.project_id}'

    def get_opportunity(self):
        return self.project.opportunity

    def descendant_ids(self):
        """This comment's id plus every reply id below it, walked level-by-level (no recursive SQL)."""
        ids = [self.pk]
        frontier = [self.pk]
        while frontier:
            frontier = list(Comment.objects.filter(parent_id__in=frontier).values_list('pk', flat=True))
            ids.extend(frontier)
        return ids


class CommentVote(models.Model):
    """One user's up/down vote on a Comment; at most one vote per (comment, author)."""

    class Value(models.IntegerChoices):
        UP = 1, 'Up'
        DOWN = -1, 'Down'

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='votes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_votes',
    )
    value = models.SmallIntegerField(choices=Value.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['comment', 'author'], name='unique_comment_vote_per_author'),
        ]

    def __str__(self):
        return f'{self.author_id} -> {self.value:+d} on Comment {self.comment_id}'
