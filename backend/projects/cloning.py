from django.db import transaction

from .models import Intervention, Opportunity, Project, Strategy

COPY_SUFFIX = ' (Copy)'


@transaction.atomic
def clone_opportunity(opportunity, owner):
    """Deep-clone an Opportunity (and all its Strategies/Interventions) for `owner`."""
    cloned = Opportunity.objects.get(pk=opportunity.pk)
    cloned.pk = None
    cloned.name = f'{opportunity.name}{COPY_SUFFIX}'
    cloned.owner = owner
    cloned.save()

    for strategy in opportunity.strategies.all():
        _clone_strategy(strategy, cloned, rename=False)

    return cloned


@transaction.atomic
def clone_strategy(strategy, target_opportunity=None):
    """Deep-clone a Strategy (and its Interventions), by default within its own Opportunity."""
    return _clone_strategy(strategy, target_opportunity or strategy.opportunity, rename=True)


def _clone_strategy(strategy, target_opportunity, rename):
    cloned = Strategy.objects.get(pk=strategy.pk)
    cloned.pk = None
    cloned.opportunity = target_opportunity
    if rename:
        cloned.name = f'{strategy.name}{COPY_SUFFIX}'
    cloned.save()

    # Clone Projects first so cloned Interventions can be re-linked to their
    # cloned counterpart below, preserving the original assignment structure
    # without touching the source Strategy's own Projects/Interventions.
    project_map = {
        project.pk: _clone_project(project, cloned, rename=False)
        for project in strategy.projects.all()
    }
    for intervention in strategy.interventions.all():
        _clone_intervention(intervention, cloned, project=project_map.get(intervention.project_id))

    return cloned


@transaction.atomic
def clone_project(project, target_strategy=None):
    """Deep-clone a Project's own fields (name/description/organizations) only.

    Its assigned Interventions are intentionally not carried over: an
    Intervention can belong to only one Project at a time, so cloning must
    not reassign interventions away from the source Project.
    """
    return _clone_project(project, target_strategy or project.strategy, rename=True)


def _clone_project(project, target_strategy, rename):
    cloned = Project.objects.get(pk=project.pk)
    cloned.pk = None
    cloned.strategy = target_strategy
    if rename:
        cloned.name = f'{project.name}{COPY_SUFFIX}'
    cloned.save()
    cloned.organizations.set(project.organizations.all())
    return cloned


def _clone_intervention(intervention, target_strategy, project=None):
    cloned = Intervention.objects.get(pk=intervention.pk)
    cloned.pk = None
    cloned.strategy = target_strategy
    cloned.project = project
    cloned.parameters = dict(intervention.parameters)
    cloned.save()
    return cloned
