from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models


def group_creates_cycle(group_pk, candidate_parent):
    """Would setting candidate_parent as group_pk's parent create a cycle?"""
    ancestor = candidate_parent
    while ancestor is not None:
        if ancestor.pk == group_pk:
            return True
        ancestor = ancestor.parent
    return False


class Group(models.Model):
    """An organization or a sub-unit within one (e.g. a department, team)."""

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subgroups',
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='administered_groups',
    )
    jcodes = models.ManyToManyField('geo.Jcode', related_name='groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'name'], name='unique_group_name_per_parent'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        # Model-level safety net (Django admin calls full_clean() automatically);
        # the API path enforces the same check explicitly in GroupSerializer.validate().
        if self.parent_id is not None and group_creates_cycle(self.pk, self.parent):
            raise ValidationError({'parent': 'A group cannot be its own ancestor.'})

    def descendant_group_ids(self):
        """This group's id plus every subgroup id, walked level-by-level (no recursive SQL)."""
        ids = [self.pk]
        frontier = [self.pk]
        while frontier:
            frontier = list(Group.objects.filter(parent_id__in=frontier).values_list('pk', flat=True))
            ids.extend(frontier)
        return ids

    def effective_members(self):
        """
        This group's own admin + members, plus every subgroup's admin +
        members. Each group's admin is tracked via the `admin` FK, not a
        Membership row, so it's unioned in separately here.
        """
        User = get_user_model()
        descendant_ids = self.descendant_group_ids()
        member_ids = set(
            Membership.objects.filter(group_id__in=descendant_ids).values_list('user_id', flat=True)
        )
        admin_ids = set(Group.objects.filter(pk__in=descendant_ids).values_list('admin_id', flat=True))
        return User.objects.filter(pk__in=member_ids | admin_ids)


class Membership(models.Model):
    """A user's membership in a Group, with a free-form list of role titles."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    roles = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group_id']
        constraints = [
            models.UniqueConstraint(fields=['user', 'group'], name='unique_membership_per_user_group'),
        ]

    def __str__(self):
        return f'{self.user_id} in {self.group_id}'
