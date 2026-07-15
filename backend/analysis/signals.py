from django.db.models.signals import post_save
from django.dispatch import receiver

from projects.models import CourseOfAction

from .models import Projection


@receiver(post_save, sender=CourseOfAction)
def create_projection(sender, instance, created, **kwargs):
    if created:
        Projection.objects.get_or_create(course_of_action=instance)
