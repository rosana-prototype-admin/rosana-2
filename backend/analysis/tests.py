from django.test import TestCase

from accounts.models import User
from focusareas.models import FocusArea, InterventionType
from projects.models import Intervention, Opportunity, Strategy

from .models import Projection
from .services import run_stub_analysis


class ProjectionAutoCreationTests(TestCase):
    def test_creating_a_strategy_auto_creates_a_pending_projection(self):
        owner = User.objects.create_user(username='owner', email='o@example.com', password='pw')
        opportunity = Opportunity.objects.create(
            name='P', focus_area=FocusArea.objects.get(name='Speed Management'), owner=owner
        )
        strategy = Strategy.objects.create(opportunity=opportunity, name='Strategy')
        self.assertTrue(Projection.objects.filter(strategy=strategy).exists())
        self.assertEqual(strategy.projection.status, Projection.Status.PENDING)


class RunStubAnalysisTests(TestCase):
    def test_stub_returns_deterministic_placeholder_shape(self):
        owner = User.objects.create_user(username='owner2', email='o2@example.com', password='pw')
        opportunity = Opportunity.objects.create(
            name='P', focus_area=FocusArea.objects.get(name='Speed Management'), owner=owner
        )
        strategy = Strategy.objects.create(opportunity=opportunity, name='Strategy')

        result = run_stub_analysis(strategy)

        self.assertEqual(result['intervention_count'], 0)
        self.assertIn('summary', result)
        self.assertIn('generated_at', result)

    def test_excluded_interventions_are_not_counted(self):
        owner = User.objects.create_user(username='owner3', email='o3@example.com', password='pw')
        focus_area = FocusArea.objects.get(name='Speed Management')
        opportunity = Opportunity.objects.create(name='P', focus_area=focus_area, owner=owner)
        strategy = Strategy.objects.create(opportunity=opportunity, name='Strategy')
        intervention_type = InterventionType.objects.create(name='Speed Camera')
        intervention_type.focus_areas.add(focus_area)

        Intervention.objects.create(
            strategy=strategy, intervention_type=intervention_type, included_in_analysis=True
        )
        Intervention.objects.create(
            strategy=strategy, intervention_type=intervention_type, included_in_analysis=False
        )

        result = run_stub_analysis(strategy)

        self.assertEqual(result['intervention_count'], 1)
