import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from groups.models import Group

from .config import CMF_UPPER_LIMIT


class CMF(models.Model):
    """A catalog CMF or a user-owned custom CMF."""

    class PermissionScope(models.TextChoices):
        AGENCY = 'agency', 'Agency'
        STATE = 'state', 'State'
        GLOBAL = 'global', 'Global'

    code = models.SlugField(max_length=100, blank=True, editable=False, unique=True)
    title = models.CharField(max_length=64)
    is_builtin = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_cmfs',
    )
    base_cmf = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='overrides',
    )
    permitted_groups = models.ManyToManyField(
        'groups.Group',
        related_name='permitted_cmfs',
        blank=True,
    )
    permission_scope = models.CharField(
        max_length=6,
        choices=PermissionScope.choices,
        default=PermissionScope.AGENCY,
    )
    # Retained because it is an existing CMF field used by the application,
    # although it is not part of the coefficient storage.
    cmf_source = models.CharField(max_length=1000, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-modified_at']
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'base_cmf'],
                condition=Q(author__isnull=False, base_cmf__isnull=False),
                name='unique_cmf_override_per_author',
            ),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f'cmf-{uuid.uuid4().hex}'
        super().save(*args, **kwargs)
        # Direct model creation (including admin/import scripts) should still
        # produce the required metadata record.
        CMFMetadata.objects.get_or_create(
            cmf=self,
            defaults={'cmf_group1': self.title},
        )

    def can_be_used_by(self, user):
        if user is None or not user.is_authenticated:
            return False
        if self.author_id == user.pk:
            return True

        if not self.is_builtin:
            return True

        try:
            plan_permissions = self.user_permissions
        except CMFUserPermission.DoesNotExist:
            plan_permissions = None
        if self.is_builtin:
            return plan_permissions is None or plan_permissions.allows(user)
        if plan_permissions is not None and plan_permissions.allows(user):
            return True
        if self.permission_scope == self.PermissionScope.GLOBAL:
            return True

        user_groups = Group.objects.filter(
            Q(admin_id=user.pk) | Q(memberships__user_id=user.pk),
        ).distinct()
        if self.permission_scope == self.PermissionScope.AGENCY:
            return self.permitted_groups.filter(pk__in=user_groups.values('pk')).exists()
        if self.permission_scope == self.PermissionScope.STATE:
            user_states = user_groups.filter(jcodes__isnull=False).values('jcodes__state')
            return self.permitted_groups.filter(jcodes__state__in=user_states).exists()
        return False

    @classmethod
    def resolve_for_user(cls, code, user):
        """Return a user's override for ``code``, or its built-in fallback."""
        builtin = cls.objects.filter(code=code, is_builtin=True).first()
        if builtin is not None and user is not None and user.is_authenticated:
            override = cls.objects.filter(author=user, base_cmf=builtin).first()
            if override is not None:
                return override

        standalone = cls.objects.filter(
            Q(code=code),
            base_cmf__isnull=True,
            is_builtin=False,
        ).first()
        if standalone is not None and standalone.can_be_used_by(user):
            return standalone
        if builtin is not None and builtin.can_be_used_by(user):
            return builtin
        return None


class CMFMetadata(models.Model):
    """The structured metadata associated with exactly one CMF."""

    class Math(models.TextChoices):
        EXPONENTIAL = 'E', 'Exponential'
        LOGARITHMIC = 'L', 'Logarithmic'
        POWER = 'P', 'Power'
        QUADRATIC = 'Q', 'Quadratic'

    cmf = models.OneToOneField(CMF, on_delete=models.CASCADE, related_name='metadata')
    cmf_group1 = models.CharField(max_length=255)
    cmf_group2 = models.CharField(max_length=255, null=True, blank=True)
    cmf_group3 = models.CharField(max_length=255, null=True, blank=True)
    descr_en_us = models.TextField(blank=True, default='')
    descr_en_au = models.TextField(blank=True, default='')
    descr_en_ca = models.TextField(blank=True, default='')
    descr_fr_ca = models.TextField(blank=True, default='')
    descr_es = models.TextField(blank=True, default='')
    cmf_math = models.CharField(max_length=1, choices=Math.choices, default=Math.QUADRATIC)
    mod_code1 = models.CharField(max_length=5, default='RFALL')
    mod_code2 = models.CharField(max_length=5, default='VTALL')
    mod_code3 = models.CharField(max_length=5, default='MCALL')
    mod_code4 = models.CharField(max_length=5, default='CCNON')
    mod_code5 = models.CharField(max_length=5, default='IXALL')
    # These values are applicability weights rather than strict flags. A
    # value of 1 means fully applicable, 0 means not applicable, and values
    # between them preserve partial/user-supplied applicability.
    age_0004 = models.FloatField(default=0.0)
    age_0509 = models.FloatField(default=0.0)
    age_1014 = models.FloatField(default=0.0)
    age_1519 = models.FloatField(default=0.0)
    age_2064 = models.FloatField(default=0.0)
    age_65up = models.FloatField(default=0.0)

    def __str__(self):
        return f'{self.cmf.code} metadata'


class CMFCoefficient(models.Model):
    """One normalized cell of the CMF 5x5x3 coefficient array."""

    class TravelMode(models.IntegerChoices):
        MOTOR_VEHICLE = 1, 'Motor vehicle occupant'
        MOTORCYCLE = 2, 'Motorcycle'
        BICYCLE = 3, 'Bicycle'
        PEDESTRIAN = 4, 'Pedestrian'
        OTHER = 5, 'Other'

    class Severity(models.TextChoices):
        FATAL = 'K', 'Fatal'
        SERIOUS = 'A', 'Serious'
        MINOR = 'B', 'Minor'
        POSSIBLE = 'C', 'Possible'
        PROPERTY_DAMAGE_ONLY = 'O', 'Property damage only'

    cmf = models.ForeignKey(CMF, on_delete=models.CASCADE, related_name='coefficients')
    travel_mode = models.PositiveSmallIntegerField(choices=TravelMode.choices)
    severity = models.CharField(max_length=1, choices=Severity.choices)
    coefficient_a = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(CMF_UPPER_LIMIT)],
    )
    coefficient_b = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(CMF_UPPER_LIMIT)],
    )
    coefficient_c = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(CMF_UPPER_LIMIT)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cmf', 'travel_mode', 'severity'],
                name='unique_cmf_coefficient_cell',
            ),
        ]
        ordering = ['travel_mode', 'severity']

    def __str__(self):
        return f'{self.cmf.code} / {self.travel_mode} / {self.severity}'


class CMFUserPermission(models.Model):
    """Plan-level access flags for one CMF."""

    cmf = models.OneToOneField(CMF, on_delete=models.CASCADE, related_name='user_permissions')
    crossroads = models.BooleanField(default=False)
    borough = models.BooleanField(default=False)
    ville = models.BooleanField(default=False)
    shire = models.BooleanField(default=False)
    provincia = models.BooleanField(default=False)
    comarca = models.BooleanField(default=False)
    metro = models.BooleanField(default=False)
    commonwealth = models.BooleanField(default=False)
    republic = models.BooleanField(default=False)

    PLAN_FIELDS = (
        'crossroads',
        'borough',
        'ville',
        'shire',
        'provincia',
        'comarca',
        'metro',
        'commonwealth',
        'republic',
    )

    @classmethod
    def field_for_user(cls, user):
        plan = (getattr(user, 'subscription_type', '') or '').lower()
        return plan if plan in cls.PLAN_FIELDS else None

    def allows(self, user):
        plan_field = self.field_for_user(user)
        return bool(plan_field and getattr(self, plan_field))
