from django.conf import settings
from django.db import models
from django.db.models import Q


class ProjectQuerySet(models.QuerySet):
    def visible_to(self, user):
        return self.filter(
            Q(owner=user) | Q(editors=user) | Q(guests=user)
        ).distinct()

    def editable_by(self, user):
        return self.filter(Q(owner=user) | Q(editors=user)).distinct()


class Project(models.Model):
    """The root object: a transportation problem under study."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    focus_area = models.ForeignKey(
        'focusareas.FocusArea',
        on_delete=models.PROTECT,
        related_name='projects',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_projects',
    )
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='editable_projects',
        blank=True,
    )
    guests = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='guest_projects',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ['-modified_at']

    def __str__(self):
        return self.name

    def get_project(self):
        return self


class CourseOfAction(models.Model):
    """One complete strategy for addressing the parent Project."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='courses_of_action',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

    def get_project(self):
        return self.project


class Intervention(models.Model):
    """One individual action within a CourseOfAction."""

    course_of_action = models.ForeignKey(
        CourseOfAction,
        on_delete=models.CASCADE,
        related_name='interventions',
    )
    intervention_type = models.ForeignKey(
        'focusareas.InterventionType',
        on_delete=models.PROTECT,
        related_name='interventions',
    )
    parameters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.intervention_type} ({self.course_of_action_id})'

    def get_project(self):
        return self.course_of_action.project
