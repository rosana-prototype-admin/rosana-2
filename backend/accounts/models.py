from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class SubscriptionType(models.TextChoices):
    NONE = 'none', 'None'
    BASIC = 'basic', 'Basic'
    PREMIUM = 'premium', 'Premium'
    ADMIN = 'admin', 'Admin'
    CROSSROADS = 'crossroads', 'Crossroads'
    BOROUGH = 'borough', 'Borough'
    VILLE = 'ville', 'Ville'
    SHIRE = 'shire', 'Shire'
    PROVINCIA = 'provincia', 'Provincia'
    COMARCA = 'comarca', 'Comarca'
    METRO = 'metro', 'Metro'
    COMMONWEALTH = 'commonwealth', 'Commonwealth'
    REPUBLIC = 'republic', 'Republic'


class SubscriptionStatus(models.TextChoices):
    TRIALING = 'trialing', 'Trialing'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    PAST_DUE = 'past_due', 'Past due'
    CANCELED = 'canceled', 'Canceled'
    EXPIRED = 'expired', 'Expired'


class SubscriptionAcquisition(models.TextChoices):
    SELF_SERVICE = 'self_service', 'Self-service'
    NEGOTIATED = 'negotiated', 'Negotiated enterprise contract'


class SubscriptionSeatType(models.TextChoices):
    TECHNICAL_USER = 'technical_user', 'Technical User'
    TECHNICAL_ADMIN = 'technical_admin', 'Technical Admin'


class ContractStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    TERMINATED = 'terminated', 'Terminated'


class Language(models.TextChoices):
    EN_AU = 'en-AU', 'English (Australia)'
    EN_CA = 'en-CA', 'English (Canada)'
    EN_GB = 'en-GB', 'English (UK)'
    EN_US = 'en-US', 'English (US)'
    FR_CA = 'fr-CA', 'Français (Canada)'
    ES_419 = 'es-419', 'Español (Latinoamericano)'


class Currency(models.TextChoices):
    AUD = 'AUD', 'Australian Dollar'
    GBP = 'GBP', 'British Pound'
    CAD = 'CAD', 'Canadian Dollar'
    EUR = 'EUR', 'Euro'
    MXN = 'MXN', 'México Peso'
    USD = 'USD', 'US Dollar'


class LengthUnit(models.TextChoices):
    METRES = 'm', 'metres'
    FEET = 'ft', 'feet'


class DistanceUnit(models.TextChoices):
    KILOMETRES = 'km', 'kilometres'
    MILES = 'mi', 'miles'


class SpeedUnit(models.TextChoices):
    KILOMETRES_PER_HOUR = 'km/h', 'kilometres per hour'
    MILES_PER_HOUR = 'mph', 'miles per hour'


class DeactivationSource(models.TextChoices):
    SELF = 'self', 'Self-deactivated'
    ADMIN = 'admin', 'Administrator-deactivated'
    SUSPENDED = 'suspended', 'Suspended'


class SmallAreaUnit(models.TextChoices):
    SQUARE_METRES = 'm2', 'square metres'
    SQUARE_FEET = 'sq ft', 'square feet'


class LargeAreaUnit(models.TextChoices):
    HECTARES = 'ha', 'hectares'
    ACRES = 'ac', 'acres'


class VolumeUnit(models.TextChoices):
    LITRES = 'L', 'litres'
    GALLONS_US = 'gal (US)', 'gallons (US)'
    GALLONS_IMPERIAL = 'gal (Imp)', 'gallons (Imperial)'


class User(AbstractUser):
    email = models.EmailField('email address', unique=True)
    # Existing accounts are treated as verified by the migration default. New
    # self-service registrations explicitly set this to False until the user
    # follows the verification link sent to their email address.
    email_verified = models.BooleanField(default=True)
    deactivation_source = models.CharField(
        max_length=20,
        choices=DeactivationSource.choices,
        blank=True,
        null=True,
        help_text='Why this account became inactive, when known.',
    )
    deactivated_at = models.DateTimeField(blank=True, null=True)
    secondary_email = models.EmailField(blank=True)
    company = models.CharField(max_length=255, blank=True)
    subscription_type = models.CharField(
        max_length=20,
        choices=SubscriptionType.choices,
        default=SubscriptionType.NONE,
    )
    language = models.CharField(max_length=6, choices=Language.choices, default=Language.EN_US)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    length_unit = models.CharField(max_length=2, choices=LengthUnit.choices, default=LengthUnit.METRES)
    distance_unit = models.CharField(max_length=2, choices=DistanceUnit.choices, default=DistanceUnit.KILOMETRES)
    speed_unit = models.CharField(max_length=5, choices=SpeedUnit.choices, default=SpeedUnit.KILOMETRES_PER_HOUR)
    area_small_unit = models.CharField(max_length=6, choices=SmallAreaUnit.choices, default=SmallAreaUnit.SQUARE_METRES)
    area_large_unit = models.CharField(max_length=2, choices=LargeAreaUnit.choices, default=LargeAreaUnit.HECTARES)
    volume_unit = models.CharField(max_length=9, choices=VolumeUnit.choices, default=VolumeUnit.LITRES)
    class Meta:
        ordering = ['username']

    def __str__(self):
        return self.username


class Plan(models.Model):
    """A configurable Rosana plan; entitlements will be attached later."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    self_service_visible = models.BooleanField(default=True)
    enterprise_available = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PlanFeature(models.Model):
    """A feature entitlement assigned to a plan."""

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='features')
    feature_code = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['plan', 'feature_code'],
                name='unique_plan_feature',
            ),
        ]
        ordering = ['plan_id', 'feature_code']

    def __str__(self):
        return f'{self.plan.code}: {self.feature_code}'


class UserSubscription(models.Model):
    """A dated subscription owned by a top-level Group organization.

    ``plan_code`` remains temporarily for backwards compatibility with the
    existing admin API and data. New code should use ``plan``.
    """

    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(
        'Plan', on_delete=models.PROTECT, null=True, blank=True, related_name='subscriptions',
    )
    plan_code = models.CharField(max_length=20, choices=SubscriptionType.choices)
    acquisition_type = models.CharField(
        max_length=20,
        choices=SubscriptionAcquisition.choices,
        default=SubscriptionAcquisition.SELF_SERVICE,
    )
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, null=True)
    seat_limit = models.PositiveIntegerField(default=1)
    external_reference = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-starts_at', '-created_at']

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.group_id and self.group.parent_id:
            raise ValidationError({'group': 'A subscription must belong to a top-level organization group.'})

    def __str__(self):
        return f'{self.group.name}: {self.plan_code} ({self.status})'


class Contract(models.Model):
    """A lightweight company contract record pending finalized legal/billing requirements."""

    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, related_name='contracts')
    subscription = models.ForeignKey(
        UserSubscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='contracts',
    )
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    external_reference = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.group_id and self.group.parent_id:
            raise ValidationError({'group': 'A contract must belong to a top-level organization group.'})
        if self.subscription_id and self.subscription.group_id != self.group_id:
            raise ValidationError({'subscription': 'The contract subscription must belong to the same organization group.'})

    def __str__(self):
        return f'{self.group.name}: {self.title}'


class SubscriptionSeat(models.Model):
    """An explicit seat assignment; group membership alone does not consume a seat."""

    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='seats')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_seats')
    seat_type = models.CharField(
        max_length=20,
        choices=SubscriptionSeatType.choices,
        default=SubscriptionSeatType.TECHNICAL_USER,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['user__username']
        constraints = [
            models.UniqueConstraint(
                fields=['subscription', 'user'],
                condition=Q(released_at__isnull=True),
                name='unique_active_subscription_seat_user',
            ),
        ]

    def __str__(self):
        return f'{self.subscription.group.name}: {self.user.username}'


class AuditEvent(models.Model):
    """Immutable record of a privileged administrative action."""

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_events')
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    group = models.ForeignKey('groups.Group', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events')
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.action} {self.entity_type} {self.entity_id}'
