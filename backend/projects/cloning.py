from django.db import transaction

from .models import Opportunity

COPY_SUFFIX = ' (Copy)'


@transaction.atomic
def clone_opportunity(opportunity, requester):
    """
    Clone an Opportunity's own fields (not its Projects/Sites/Strategies).
    lead_agency/manager/focus_area/specific_focus_area carry over unchanged
    via the pk=None trick; assoc_agencies (M2M) needs an explicit copy.
    delegates/stakeholders are deliberately NOT copied -- if the requester
    isn't already the manager, they're added as a delegate so they retain
    write access to the copy they just made.
    """
    cloned = Opportunity.objects.get(pk=opportunity.pk)
    cloned.pk = None
    cloned.title = f'{opportunity.title}{COPY_SUFFIX}'
    cloned.save()
    cloned.assoc_agencies.set(opportunity.assoc_agencies.all())
    if requester.pk != cloned.manager_id:
        cloned.delegates.add(requester)
    return cloned
