from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from focusareas.models import FocusArea, InterventionType

from .models import CourseOfAction, Intervention, Project


class ProjectHierarchyTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='pw')
        self.editor = User.objects.create_user(username='editor', email='editor@example.com', password='pw')
        self.guest = User.objects.create_user(username='guest', email='guest@example.com', password='pw')
        self.stranger = User.objects.create_user(username='stranger', email='stranger@example.com', password='pw')

        self.vru = FocusArea.objects.get(name='Vulnerable Road Users')
        self.speed = FocusArea.objects.get(name='Speed Management')

        self.valid_type = InterventionType.objects.create(name='Crossing Improvement')
        self.valid_type.focus_areas.add(self.vru)
        self.invalid_type = InterventionType.objects.create(name='Speed Camera')
        self.invalid_type.focus_areas.add(self.speed)

        self.project = Project.objects.create(
            name='Test Project', focus_area=self.vru, owner=self.owner
        )
        self.project.editors.add(self.editor)
        self.project.guests.add(self.guest)

        self.coa = CourseOfAction.objects.create(project=self.project, name='COA 1')
        self.intervention = Intervention.objects.create(
            course_of_action=self.coa, intervention_type=self.valid_type, parameters={'count': 1}
        )


class ProjectPermissionTests(ProjectHierarchyTestCase):
    def test_owner_can_read_and_write(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(f'/api/projects/{self.project.pk}/', {'name': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_editor_can_read_and_write(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(f'/api/projects/{self.project.pk}/', {'name': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_guest_can_read_but_not_write(self):
        self.client.force_authenticate(user=self.guest)
        read_response = self.client.get(f'/api/projects/{self.project.pk}/')
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)

        write_response = self.client.patch(f'/api/projects/{self.project.pk}/', {'name': 'Hacked'})
        self.assertEqual(write_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_cannot_read(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(f'/api/projects/{self.project.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_project_list_is_scoped_per_user(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get('/api/projects/')
        self.assertEqual(len(response.data), 0)

        self.client.force_authenticate(user=self.guest)
        response = self.client.get('/api/projects/')
        self.assertEqual(len(response.data), 1)

    def test_create_project_sets_owner_automatically(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(
            '/api/projects/',
            {'name': 'New Project', 'description': '', 'focus_area': self.vru.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner'], self.stranger.pk)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NestedCreationTests(ProjectHierarchyTestCase):
    def test_coa_must_be_created_via_nested_route(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post('/api/courses-of-action/', {'name': 'Flat create'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_coa_created_via_nested_route_auto_links_project(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/projects/{self.project.pk}/courses-of-action/', {'name': 'COA 2'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['project'], self.project.pk)
        self.assertIn('projection', response.data)

    def test_guest_cannot_create_coa(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(
            f'/api/projects/{self.project.pk}/courses-of-action/', {'name': 'Should fail'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_intervention_rejected_for_mismatched_focus_area(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/courses-of-action/{self.coa.pk}/interventions/',
            {'intervention_type': self.invalid_type.pk, 'parameters': {}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_intervention_accepted_for_matching_focus_area(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/courses-of-action/{self.coa.pk}/interventions/',
            {'intervention_type': self.valid_type.pk, 'parameters': {'lanes': 2}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['course_of_action'], self.coa.pk)


class CloningTests(ProjectHierarchyTestCase):
    def test_clone_project_deep_copies_hierarchy_with_new_owner(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/projects/{self.project.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cloned_project = Project.objects.get(pk=response.data['id'])
        self.assertNotEqual(cloned_project.pk, self.project.pk)
        self.assertEqual(cloned_project.owner, self.owner)
        self.assertEqual(cloned_project.editors.count(), 0)
        self.assertEqual(cloned_project.guests.count(), 0)

        cloned_coas = list(cloned_project.courses_of_action.all())
        self.assertEqual(len(cloned_coas), 1)
        self.assertNotEqual(cloned_coas[0].pk, self.coa.pk)

        cloned_interventions = list(cloned_coas[0].interventions.all())
        self.assertEqual(len(cloned_interventions), 1)
        self.assertNotEqual(cloned_interventions[0].pk, self.intervention.pk)
        self.assertEqual(cloned_interventions[0].parameters, self.intervention.parameters)

        # Original untouched.
        self.project.refresh_from_db()
        self.assertEqual(self.project.courses_of_action.count(), 1)

    def test_guest_can_clone_project_read_only_is_sufficient(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(f'/api/projects/{self.project.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner'], self.guest.pk)

    def test_guest_cannot_clone_course_of_action(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(f'/api/courses-of-action/{self.coa.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_clone_course_of_action_gets_fresh_projection(self):
        self.client.force_authenticate(user=self.owner)
        self.client.post(f'/api/courses-of-action/{self.coa.pk}/run-analysis/')
        response = self.client.post(f'/api/courses-of-action/{self.coa.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['projection']['status'], 'pending')


class RunAnalysisTests(ProjectHierarchyTestCase):
    def test_run_analysis_completes_projection_with_placeholder_data(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/courses-of-action/{self.coa.pk}/run-analysis/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'complete')
        self.assertIsNotNone(response.data['computed_at'])
        self.assertEqual(response.data['result_data']['intervention_count'], 1)

    def test_guest_cannot_run_analysis(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(f'/api/courses-of-action/{self.coa.pk}/run-analysis/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class QueryEfficiencyTests(ProjectHierarchyTestCase):
    def test_project_detail_query_count_does_not_scale_with_children(self):
        self.client.force_authenticate(user=self.owner)

        with CaptureQueriesContext(connection) as small:
            self.client.get(f'/api/projects/{self.project.pk}/courses-of-action/')
        baseline = len(small.captured_queries)

        for i in range(10):
            coa = CourseOfAction.objects.create(project=self.project, name=f'Extra COA {i}')
            Intervention.objects.create(
                course_of_action=coa, intervention_type=self.valid_type, parameters={}
            )

        with CaptureQueriesContext(connection) as large:
            self.client.get(f'/api/projects/{self.project.pk}/courses-of-action/')

        self.assertEqual(len(large.captured_queries), baseline)
