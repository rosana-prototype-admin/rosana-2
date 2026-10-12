from django.db.models.signals import post_save
from django.dispatch import receiver

from projects.models import Strategy

from .models import Projection


@receiver(post_save, sender=Strategy)
def create_projection(sender, instance, created, **kwargs):
    if created:
        Projection.objects.get_or_create(strategy=instance)
