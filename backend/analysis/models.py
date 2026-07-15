from django.db import models


class Projection(models.Model):
    """The (currently stubbed) analysis result for a CourseOfAction."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETE = 'complete', 'Complete'
        FAILED = 'failed', 'Failed'

    course_of_action = models.OneToOneField(
        'projects.CourseOfAction',
        on_delete=models.CASCADE,
        related_name='projection',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    result_data = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Projection for {self.course_of_action_id} ({self.status})'
