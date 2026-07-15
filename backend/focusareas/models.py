from django.db import models


class FocusArea(models.Model):
    """One node in the Focus Area taxonomy tree (see supporting docs for the full hierarchy)."""

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE,
    )
    level = models.PositiveSmallIntegerField(editable=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['level', 'parent_id', 'order']
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'name'],
                name='unique_focusarea_name_per_parent',
            ),
        ]

    def save(self, *args, **kwargs):
        self.level = 1 if self.parent_id is None else self.parent.level + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class InterventionType(models.Model):
    """Admin-managed catalog of intervention types, constrained to applicable focus areas."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    focus_areas = models.ManyToManyField(
        FocusArea,
        related_name='intervention_types',
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
