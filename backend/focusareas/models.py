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
    """
    Admin-managed catalog of intervention types, constrained to applicable
    focus areas. `name` alone is not unique: the same category can pair with
    different names, and -- more importantly -- the same (name, category)
    pair can independently apply to more than one focus area (e.g. "Drug-
    Impaired Driving Laws" / "Policy" applies to both Cannabis and Other
    Drugs), in which case it's one row with multiple focus_areas rather than
    duplicate rows.
    """

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True)
    cmf = models.ForeignKey(
        'cmfs.CMF',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='intervention_types',
    )
    focus_areas = models.ManyToManyField(
        FocusArea,
        related_name='intervention_types',
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']
        constraints = [
            models.UniqueConstraint(fields=['name', 'category'], name='unique_interventiontype_name_category'),
        ]

    def __str__(self):
        return f'{self.category} - {self.name}' if self.category else self.name
