from django.contrib.auth.models import AbstractUser
from django.db import models


class SubscriptionType(models.TextChoices):
    NONE = 'none', 'None'
    BASIC = 'basic', 'Basic'
    PREMIUM = 'premium', 'Premium'
    ADMIN = 'admin', 'Admin'


class User(AbstractUser):
    email = models.EmailField('email address', unique=True)
    secondary_email = models.EmailField(blank=True)
    company = models.CharField(max_length=255, blank=True)
    subscription_type = models.CharField(
        max_length=20,
        choices=SubscriptionType.choices,
        default=SubscriptionType.NONE,
    )
    jcodes = models.ManyToManyField(
        'geo.Jcode',
        related_name='users',
        blank=True,
    )

    class Meta:
        ordering = ['username']

    def __str__(self):
        return self.username
