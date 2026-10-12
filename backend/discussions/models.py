from django.conf import settings
from django.db import models


class Comment(models.Model):
    """A threaded comment on an Opportunity, with replies capped at MAX_DEPTH."""

    MAX_DEPTH = 3  # root = depth 0, deepest reply = depth 3

    opportunity = models.ForeignKey(
        'projects.Opportunity',
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
    body = models.TextField()
    depth = models.PositiveSmallIntegerField(default=0)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['opportunity', 'parent']),
            models.Index(fields=['opportunity', 'created_at']),
        ]

    def __str__(self):
        return f'Comment {self.pk} on Opportunity {self.opportunity_id}'

    def get_opportunity(self):
        return self.opportunity


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
