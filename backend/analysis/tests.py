from django.test import TestCase

from accounts.models import User
from focusareas.models import FocusArea
from projects.models import CourseOfAction, Project

from .models import Projection
from .services import run_stub_analysis


class ProjectionAutoCreationTests(TestCase):
    def test_creating_a_course_of_action_auto_creates_a_pending_projection(self):
        owner = User.objects.create_user(username='owner', email='o@example.com', password='pw')
        project = Project.objects.create(
            name='P', focus_area=FocusArea.objects.get(name='Speed Management'), owner=owner
        )
        coa = CourseOfAction.objects.create(project=project, name='COA')
        self.assertTrue(Projection.objects.filter(course_of_action=coa).exists())
        self.assertEqual(coa.projection.status, Projection.Status.PENDING)


class RunStubAnalysisTests(TestCase):
    def test_stub_returns_deterministic_placeholder_shape(self):
        owner = User.objects.create_user(username='owner2', email='o2@example.com', password='pw')
        project = Project.objects.create(
            name='P', focus_area=FocusArea.objects.get(name='Speed Management'), owner=owner
        )
        coa = CourseOfAction.objects.create(project=project, name='COA')

        result = run_stub_analysis(coa)

        self.assertEqual(result['intervention_count'], 0)
        self.assertIn('summary', result)
        self.assertIn('generated_at', result)
