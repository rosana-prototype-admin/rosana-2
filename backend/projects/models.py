from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator

from focusareas.models import InterventionType


class OpportunityQuerySet(models.QuerySet):
    def visible_to(self, user):
        return self.filter(
            Q(manager=user)
            | Q(delegates=user)
            | Q(stakeholders=user)
            | Q(assoc_agencies__admin=user)
            | Q(assoc_agencies__memberships__user=user)
        ).distinct()

    def editable_by(self, user):
        return self.filter(Q(manager=user) | Q(delegates=user)).distinct()


class Opportunity(models.Model):
    """The root object: a transportation problem under study."""

    class Status(models.TextChoices):
        DRAFTING = 'drafting', 'Drafting'
        REVIEW = 'review', 'Review'
        IMPLEMENTATION = 'implementation', 'Implementation'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=100)
    comment = models.CharField(max_length=1000, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFTING)
    lead_agency = models.ForeignKey(
        'groups.Group',
        on_delete=models.PROTECT,
        related_name='led_opportunities',
    )
    assoc_agencies = models.ManyToManyField(
        'groups.Group',
        related_name='assoc_opportunities',
        blank=True,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_opportunities',
    )
    delegates = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='delegate_opportunities',
        blank=True,
    )
    stakeholders = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='stakeholder_opportunities',
        blank=True,
    )
    focus_area = models.ForeignKey(
        'focusareas.FocusArea',
        on_delete=models.PROTECT,
        related_name='opportunities',
    )
    specific_focus_area = models.ForeignKey(
        'focusareas.FocusArea',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = OpportunityQuerySet.as_manager()

    class Meta:
        ordering = ['-modified_at']

    def __str__(self):
        return self.title

    def get_opportunity(self):
        return self


class Project(models.Model):
    """A body of work under an Opportunity, made up of one or more Sites."""

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=100)
    comment = models.CharField(max_length=1000, blank=True)
    status = models.IntegerField(default=0)
    comments_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-modified_at']

    def __str__(self):
        return self.title

    def get_opportunity(self):
        return self.opportunity


# Fixed row-major order for Site.casualty_obs / Site.casualty_est. The rows
# correspond to the CMF road-user types and each row contains the five CMF
# injury columns.
CASUALTY_TABLE_SIZE = 25


def default_casualty_array():
    return [0] * CASUALTY_TABLE_SIZE


class Site(models.Model):
    """A geographic location, belonging to a Project, where intervention work is intended."""

    class CasualtyDataType(models.TextChoices):
        CASUALTY_DAMAGE = 'casualty-damage', 'Casualty / damage counts'
        CRASH = 'crash', 'Crash counts'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sites')
    jcode = models.ForeignKey(
        'geo.Jcode',
        related_name='sites',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=100)
    comment = models.CharField(max_length=1000, blank=True)
    site_type = models.CharField(max_length=5, default='RFALL')
    road_class = models.CharField(max_length=255, blank=True)
    segment_length = models.FloatField(null=True, blank=True)
    segment_length_unit = models.CharField(
        max_length=11,
        choices=[
            ('meters', 'Meters'),
            ('feet', 'Feet'),
            ('kilometers', 'Kilometers'),
            ('miles', 'Miles'),
        ],
        default='meters',
    )
    gps_x = models.FloatField(null=True, blank=True)
    gps_y = models.FloatField(null=True, blank=True)
    gps_z = models.FloatField(default=0)
    aadt = models.FloatField(null=True, blank=True)
    tev = models.IntegerField(null=True, blank=True)
    casualty_data_type = models.CharField(
        max_length=16,
        choices=CasualtyDataType.choices,
        default=CasualtyDataType.CASUALTY_DAMAGE,
    )
    casualty_obs = ArrayField(
        models.IntegerField(validators=[MinValueValidator(0)]),
        size=CASUALTY_TABLE_SIZE,
        default=default_casualty_array,
        blank=True,
    )
    casualty_est = ArrayField(
        models.IntegerField(validators=[MinValueValidator(0)]),
        size=CASUALTY_TABLE_SIZE,
        default=default_casualty_array,
        blank=True,
    )
    casualty_time_years = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(25)],
    )
    casualty_time_months = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-modified_at']

    def __str__(self):
        return self.title

    def get_opportunity(self):
        return self.project.opportunity

    def sync_strategies(self):
        """
        Ensure a Strategy row exists for every InterventionType compatible
        with this Site's Opportunity's focus area. Strategy rows are never
        created/deleted by users (the compatible set is fixed, derived from
        the Opportunity's immutable focus area) -- this is the only place
        rows get created, and it's safe to call on every read: it's a no-op
        once everything currently compatible already has a row, and it picks
        up any InterventionType rows added to the catalog later.
        """
        opportunity = self.get_opportunity()
        effective_focus_area_id = opportunity.specific_focus_area_id or opportunity.focus_area_id
        compatible_ids = set(
            InterventionType.objects.filter(
                focus_areas=effective_focus_area_id, is_active=True
            ).values_list('pk', flat=True)
        )
        existing_ids = set(self.strategies.values_list('intervention_type_id', flat=True))
        missing_ids = compatible_ids - existing_ids
        if missing_ids:
            Strategy.objects.bulk_create(
                [Strategy(site=self, intervention_type_id=pk) for pk in missing_ids]
            )


class Strategy(models.Model):
    """
    One InterventionType applicable to a Site, given the Site's Opportunity's
    focus area (see Site.sync_strategies -- rows are auto-provisioned, never
    user-created/deleted). `selected` is the user-facing checkbox: whether
    this strategy actually applies at this site. `details` holds whatever
    per-site, per-strategy data gets defined later -- undefined for now.
    """

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='strategies')
    intervention_type = models.ForeignKey(
        'focusareas.InterventionType',
        on_delete=models.PROTECT,
        related_name='strategies',
    )
    selected = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-modified_at']
        constraints = [
            models.UniqueConstraint(fields=['site', 'intervention_type'], name='unique_strategy_per_site_intervention_type'),
        ]

    def __str__(self):
        return str(self.intervention_type)

    def get_opportunity(self):
        return self.site.project.opportunity
