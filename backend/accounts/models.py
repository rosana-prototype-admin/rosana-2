from django.contrib.auth.models import AbstractUser
from django.db import models


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
