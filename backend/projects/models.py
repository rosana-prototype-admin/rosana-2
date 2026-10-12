from django.conf import settings
from django.db import models
from django.db.models import Q


class OpportunityQuerySet(models.QuerySet):
    def visible_to(self, user):
        return self.filter(
            Q(owner=user) | Q(editors=user) | Q(guests=user)
        ).distinct()

    def editable_by(self, user):
        return self.filter(Q(owner=user) | Q(editors=user)).distinct()


class Opportunity(models.Model):
    """The root object: a transportation problem under study."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    focus_area = models.ForeignKey(
        'focusareas.FocusArea',
        on_delete=models.PROTECT,
        related_name='opportunities',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_opportunities',
    )
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='editable_opportunities',
        blank=True,
    )
    guests = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='guest_opportunities',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = OpportunityQuerySet.as_manager()

    class Meta:
        ordering = ['-modified_at']

    def __str__(self):
        return self.name

    def get_opportunity(self):
        return self


class Strategy(models.Model):
    """One complete strategy for addressing the parent Opportunity."""

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='strategies',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

    def get_opportunity(self):
        return self.opportunity


class Organization(models.Model):
    """A reusable, freeform catalog entry for organizations affiliated with Projects."""

    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Project(models.Model):
    """An organizational attempt at a set of Interventions within a Strategy."""

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name='projects',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organizations = models.ManyToManyField(
        Organization,
        related_name='projects',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

    def get_opportunity(self):
        return self.strategy.opportunity


class Intervention(models.Model):
    """One individual action within a Strategy."""

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name='interventions',
    )
    intervention_type = models.ForeignKey(
        'focusareas.InterventionType',
        on_delete=models.PROTECT,
        related_name='interventions',
    )
    parameters = models.JSONField(default=dict, blank=True)
    included_in_analysis = models.BooleanField(default=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interventions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.intervention_type} ({self.strategy_id})'

    def get_opportunity(self):
        return self.strategy.opportunity
