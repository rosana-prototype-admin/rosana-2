from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from focusareas.models import FocusArea, InterventionType

from .models import Intervention, Opportunity, Organization, Project, Strategy
from .permissions import can_invite, can_manage_roles


class OpportunityHierarchyTestCase(APITestCase):
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

        self.opportunity = Opportunity.objects.create(
            name='Test Opportunity', focus_area=self.vru, owner=self.owner
        )
        self.opportunity.editors.add(self.editor)
        self.opportunity.guests.add(self.guest)

        self.strategy = Strategy.objects.create(opportunity=self.opportunity, name='Strategy 1')
        self.intervention = Intervention.objects.create(
            strategy=self.strategy, intervention_type=self.valid_type, parameters={'count': 1}
        )


class OpportunityPermissionTests(OpportunityHierarchyTestCase):
    def test_owner_can_read_and_write(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(f'/api/opportunities/{self.opportunity.pk}/', {'name': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_editor_can_read_and_write(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(f'/api/opportunities/{self.opportunity.pk}/', {'name': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_guest_can_read_but_not_write(self):
        self.client.force_authenticate(user=self.guest)
        read_response = self.client.get(f'/api/opportunities/{self.opportunity.pk}/')
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)

        write_response = self.client.patch(f'/api/opportunities/{self.opportunity.pk}/', {'name': 'Hacked'})
        self.assertEqual(write_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_cannot_read(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(f'/api/opportunities/{self.opportunity.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_opportunity_list_is_scoped_per_user(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get('/api/opportunities/')
        self.assertEqual(len(response.data), 0)

        self.client.force_authenticate(user=self.guest)
        response = self.client.get('/api/opportunities/')
        self.assertEqual(len(response.data), 1)

    def test_create_opportunity_sets_owner_automatically(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(
            '/api/opportunities/',
            {'name': 'New Opportunity', 'description': '', 'focus_area': self.vru.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner'], self.stranger.pk)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get('/api/opportunities/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MembershipPermissionTests(OpportunityHierarchyTestCase):
    def test_only_owner_can_invite(self):
        self.assertTrue(can_invite(self.owner, self.opportunity))
        self.assertFalse(can_invite(self.editor, self.opportunity))
        self.assertFalse(can_invite(self.guest, self.opportunity))
        self.assertFalse(can_invite(self.stranger, self.opportunity))

    def test_only_owner_can_manage_roles(self):
        self.assertTrue(can_manage_roles(self.owner, self.opportunity))
        self.assertFalse(can_manage_roles(self.editor, self.opportunity))
        self.assertFalse(can_manage_roles(self.guest, self.opportunity))
        self.assertFalse(can_manage_roles(self.stranger, self.opportunity))


class MembershipEndpointTests(OpportunityHierarchyTestCase):
    def members_url(self, opportunity=None):
        return f'/api/opportunities/{(opportunity or self.opportunity).pk}/members/'

    def member_detail_url(self, user, opportunity=None):
        return f'/api/opportunities/{(opportunity or self.opportunity).pk}/members/{user.pk}/'

    def test_owner_can_list_members(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roles = {member['username']: member['role'] for member in response.data}
        self.assertEqual(roles, {'owner': 'owner', 'editor': 'editor', 'guest': 'guest'})

    def test_guest_can_list_members(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_list_members(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_invite_new_editor(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.members_url(), {'identifier': self.stranger.username, 'role': 'editor'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.opportunity.editors.filter(pk=self.stranger.pk).exists())

    def test_owner_can_invite_by_email(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.members_url(), {'identifier': self.stranger.email, 'role': 'guest'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.opportunity.guests.filter(pk=self.stranger.pk).exists())

    def test_editor_cannot_invite(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post(
            self.members_url(), {'identifier': self.stranger.username, 'role': 'editor'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_nonexistent_user_fails(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.members_url(), {'identifier': 'nobody', 'role': 'editor'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invite_existing_member_fails(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.members_url(), {'identifier': self.guest.username, 'role': 'editor'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invite_owner_fails(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.members_url(), {'identifier': self.owner.username, 'role': 'editor'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_can_change_member_role(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(self.member_detail_url(self.guest), {'role': 'editor'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.opportunity.editors.filter(pk=self.guest.pk).exists())
        self.assertFalse(self.opportunity.guests.filter(pk=self.guest.pk).exists())

    def test_editor_cannot_change_role(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(self.member_detail_url(self.guest), {'role': 'editor'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_role_for_non_member_is_not_found(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(self.member_detail_url(self.stranger), {'role': 'editor'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_remove_member(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.member_detail_url(self.editor))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.opportunity.editors.filter(pk=self.editor.pk).exists())

    def test_guest_cannot_remove_member(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.delete(self.member_detail_url(self.editor))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class NestedCreationTests(OpportunityHierarchyTestCase):
    def test_strategy_must_be_created_via_nested_route(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post('/api/strategies/', {'name': 'Flat create'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_strategy_created_via_nested_route_auto_links_opportunity(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/opportunities/{self.opportunity.pk}/strategies/', {'name': 'Strategy 2'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['opportunity'], self.opportunity.pk)
        self.assertIn('projection', response.data)

    def test_guest_cannot_create_strategy(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(
            f'/api/opportunities/{self.opportunity.pk}/strategies/', {'name': 'Should fail'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_intervention_rejected_for_mismatched_focus_area(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/strategies/{self.strategy.pk}/interventions/',
            {'intervention_type': self.invalid_type.pk, 'parameters': {}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_intervention_accepted_for_matching_focus_area(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/strategies/{self.strategy.pk}/interventions/',
            {'intervention_type': self.valid_type.pk, 'parameters': {'lanes': 2}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['strategy'], self.strategy.pk)


class InterventionSyncTests(OpportunityHierarchyTestCase):
    def test_listing_interventions_backfills_missing_compatible_types(self):
        other_type = InterventionType.objects.create(name='Refuge Island')
        other_type.focus_areas.add(self.vru)

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/api/strategies/{self.strategy.pk}/interventions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Only assert our own fixture types are present: focusareas' seed
        # migration also ships real InterventionTypes that may independently
        # be compatible with the same (real) 'Vulnerable Road Users' focus
        # area, and the sync is expected to backfill those too.
        types_present = {row['intervention_type'] for row in response.data}
        self.assertIn(self.valid_type.pk, types_present)
        self.assertIn(other_type.pk, types_present)
        self.assertTrue(
            Intervention.objects.filter(strategy=self.strategy, intervention_type=other_type).exists()
        )

    def test_listing_interventions_does_not_duplicate_existing_rows(self):
        self.client.force_authenticate(user=self.owner)
        self.client.get(f'/api/strategies/{self.strategy.pk}/interventions/')
        first_count = Intervention.objects.filter(strategy=self.strategy).count()

        response = self.client.get(f'/api/strategies/{self.strategy.pk}/interventions/')

        self.assertEqual(
            Intervention.objects.filter(strategy=self.strategy, intervention_type=self.valid_type).count(), 1
        )
        self.assertEqual(Intervention.objects.filter(strategy=self.strategy).count(), first_count)
        self.assertEqual(len(response.data), first_count)

    def test_listing_interventions_ignores_incompatible_types(self):
        self.client.force_authenticate(user=self.owner)
        self.client.get(f'/api/strategies/{self.strategy.pk}/interventions/')
        self.assertFalse(
            Intervention.objects.filter(strategy=self.strategy, intervention_type=self.invalid_type).exists()
        )

    def test_guest_can_list_and_triggers_sync(self):
        other_type = InterventionType.objects.create(name='Refuge Island')
        other_type.focus_areas.add(self.vru)

        self.client.force_authenticate(user=self.guest)
        response = self.client.get(f'/api/strategies/{self.strategy.pk}/interventions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types_present = {row['intervention_type'] for row in response.data}
        self.assertIn(self.valid_type.pk, types_present)
        self.assertIn(other_type.pk, types_present)

    def test_auto_created_intervention_defaults_to_included(self):
        other_type = InterventionType.objects.create(name='Refuge Island')
        other_type.focus_areas.add(self.vru)

        self.client.force_authenticate(user=self.owner)
        self.client.get(f'/api/strategies/{self.strategy.pk}/interventions/')
        created = Intervention.objects.get(strategy=self.strategy, intervention_type=other_type)
        self.assertTrue(created.included_in_analysis)

    def test_owner_can_toggle_included_in_analysis(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f'/api/interventions/{self.intervention.pk}/', {'included_in_analysis': False}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['included_in_analysis'])
        self.intervention.refresh_from_db()
        self.assertFalse(self.intervention.included_in_analysis)

    def test_guest_cannot_toggle_included_in_analysis(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.patch(
            f'/api/interventions/{self.intervention.pk}/', {'included_in_analysis': False}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProjectTests(OpportunityHierarchyTestCase):
    def test_project_must_be_created_via_nested_route(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post('/api/projects/', {'name': 'Flat create'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_project_created_via_nested_route_auto_links_strategy(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/strategies/{self.strategy.pk}/projects/', {'name': 'Project 1'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['strategy'], self.strategy.pk)
        self.assertEqual(response.data['interventions'], [])
        self.assertEqual(response.data['organizations'], [])

    def test_guest_cannot_create_project(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(
            f'/api/strategies/{self.strategy.pk}/projects/', {'name': 'Should fail'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_project_with_organizations(self):
        org = Organization.objects.create(name='City of Raleigh DOT')
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/strategies/{self.strategy.pk}/projects/',
            {'name': 'Project 1', 'organization_ids': [org.pk]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual([o['id'] for o in response.data['organizations']], [org.pk])

    def test_organization_search_by_name(self):
        Organization.objects.create(name='City of Raleigh DOT')
        Organization.objects.create(name='NCDOT')
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/organizations/', {'q': 'raleigh'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'City of Raleigh DOT')

    def test_owner_can_assign_intervention_to_project(self):
        project = Project.objects.create(strategy=self.strategy, name='Project 1')
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f'/api/interventions/{self.intervention.pk}/', {'project': project.pk}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['project'], project.pk)
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.project_id, project.pk)

    def test_owner_can_unassign_intervention_from_project(self):
        project = Project.objects.create(strategy=self.strategy, name='Project 1')
        self.intervention.project = project
        self.intervention.save(update_fields=['project'])

        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f'/api/interventions/{self.intervention.pk}/', {'project': None}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['project'])

    def test_cannot_assign_intervention_to_project_from_another_strategy(self):
        other_strategy = Strategy.objects.create(opportunity=self.opportunity, name='Strategy 2')
        other_project = Project.objects.create(strategy=other_strategy, name='Other Project')

        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f'/api/interventions/{self.intervention.pk}/', {'project': other_project.pk}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleting_project_sets_intervention_project_to_null(self):
        project = Project.objects.create(strategy=self.strategy, name='Project 1')
        self.intervention.project = project
        self.intervention.save(update_fields=['project'])

        project.delete()

        self.intervention.refresh_from_db()
        self.assertIsNone(self.intervention.project)

    def test_owner_can_clone_project_without_carrying_over_interventions(self):
        project = Project.objects.create(strategy=self.strategy, name='Project 1')
        org = Organization.objects.create(name='City of Raleigh DOT')
        project.organizations.add(org)
        self.intervention.project = project
        self.intervention.save(update_fields=['project'])

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/projects/{project.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Project 1 (Copy)')
        self.assertEqual([o['id'] for o in response.data['organizations']], [org.pk])
        self.assertEqual(response.data['interventions'], [])

        # The source project's own assignment is untouched by cloning.
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.project_id, project.pk)

    def test_guest_cannot_clone_project(self):
        project = Project.objects.create(strategy=self.strategy, name='Project 1')
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(f'/api/projects/{project.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CloningTests(OpportunityHierarchyTestCase):
    def test_clone_opportunity_deep_copies_hierarchy_with_new_owner(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/opportunities/{self.opportunity.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cloned_opportunity = Opportunity.objects.get(pk=response.data['id'])
        self.assertNotEqual(cloned_opportunity.pk, self.opportunity.pk)
        self.assertEqual(cloned_opportunity.owner, self.owner)
        self.assertEqual(cloned_opportunity.editors.count(), 0)
        self.assertEqual(cloned_opportunity.guests.count(), 0)

        cloned_strategies = list(cloned_opportunity.strategies.all())
        self.assertEqual(len(cloned_strategies), 1)
        self.assertNotEqual(cloned_strategies[0].pk, self.strategy.pk)

        cloned_interventions = list(cloned_strategies[0].interventions.all())
        self.assertEqual(len(cloned_interventions), 1)
        self.assertNotEqual(cloned_interventions[0].pk, self.intervention.pk)
        self.assertEqual(cloned_interventions[0].parameters, self.intervention.parameters)

        # Original untouched.
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.strategies.count(), 1)

    def test_guest_can_clone_opportunity_read_only_is_sufficient(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(f'/api/opportunities/{self.opportunity.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner'], self.guest.pk)

    def test_guest_cannot_clone_strategy(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(f'/api/strategies/{self.strategy.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_clone_strategy_gets_fresh_projection(self):
        self.client.force_authenticate(user=self.owner)
        self.client.post(f'/api/strategies/{self.strategy.pk}/run-analysis/')
        response = self.client.post(f'/api/strategies/{self.strategy.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['projection']['status'], 'pending')

    def test_clone_strategy_re_links_cloned_interventions_to_cloned_projects(self):
        project = Project.objects.create(strategy=self.strategy, name='Project 1')
        self.intervention.project = project
        self.intervention.save(update_fields=['project'])

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/strategies/{self.strategy.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cloned_strategy = Strategy.objects.get(pk=response.data['id'])
        cloned_projects = list(cloned_strategy.projects.all())
        self.assertEqual(len(cloned_projects), 1)
        self.assertNotEqual(cloned_projects[0].pk, project.pk)
        self.assertEqual(cloned_projects[0].name, 'Project 1')  # not re-suffixed when cascading

        cloned_intervention = cloned_strategy.interventions.get()
        self.assertEqual(cloned_intervention.project_id, cloned_projects[0].pk)

        # Original untouched.
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.project_id, project.pk)


class RunAnalysisTests(OpportunityHierarchyTestCase):
    def test_run_analysis_completes_projection_with_placeholder_data(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/strategies/{self.strategy.pk}/run-analysis/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'complete')
        self.assertIsNotNone(response.data['computed_at'])
        self.assertEqual(response.data['result_data']['intervention_count'], 1)

    def test_guest_cannot_run_analysis(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(f'/api/strategies/{self.strategy.pk}/run-analysis/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class QueryEfficiencyTests(OpportunityHierarchyTestCase):
    def test_opportunity_detail_query_count_does_not_scale_with_children(self):
        self.client.force_authenticate(user=self.owner)

        with CaptureQueriesContext(connection) as small:
            self.client.get(f'/api/opportunities/{self.opportunity.pk}/strategies/')
        baseline = len(small.captured_queries)

        for i in range(10):
            strategy = Strategy.objects.create(opportunity=self.opportunity, name=f'Extra Strategy {i}')
            Intervention.objects.create(
                strategy=strategy, intervention_type=self.valid_type, parameters={}
            )

        with CaptureQueriesContext(connection) as large:
            self.client.get(f'/api/opportunities/{self.opportunity.pk}/strategies/')

        self.assertEqual(len(large.captured_queries), baseline)
