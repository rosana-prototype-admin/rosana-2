from django.db import transaction

from .models import CourseOfAction, Intervention, Project

COPY_SUFFIX = ' (Copy)'


@transaction.atomic
def clone_project(project, owner):
    """Deep-clone a Project (and all its CoursesOfAction/Interventions) for `owner`."""
    cloned = Project.objects.get(pk=project.pk)
    cloned.pk = None
    cloned.name = f'{project.name}{COPY_SUFFIX}'
    cloned.owner = owner
    cloned.save()

    for coa in project.courses_of_action.all():
        _clone_course_of_action(coa, cloned, rename=False)

    return cloned


@transaction.atomic
def clone_course_of_action(coa, target_project=None):
    """Deep-clone a CourseOfAction (and its Interventions), by default within its own Project."""
    return _clone_course_of_action(coa, target_project or coa.project, rename=True)


def _clone_course_of_action(coa, target_project, rename):
    cloned = CourseOfAction.objects.get(pk=coa.pk)
    cloned.pk = None
    cloned.project = target_project
    if rename:
        cloned.name = f'{coa.name}{COPY_SUFFIX}'
    cloned.save()

    for intervention in coa.interventions.all():
        _clone_intervention(intervention, cloned)

    return cloned


@transaction.atomic
def clone_intervention(intervention, target_course_of_action=None):
    return _clone_intervention(
        intervention, target_course_of_action or intervention.course_of_action
    )


def _clone_intervention(intervention, target_coa):
    cloned = Intervention.objects.get(pk=intervention.pk)
    cloned.pk = None
    cloned.course_of_action = target_coa
    cloned.parameters = dict(intervention.parameters)
    cloned.save()
    return cloned
