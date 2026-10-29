from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from geo.models import Jcode
from focusareas.models import FocusArea, InterventionType
from groups.models import Group, Membership

from .models import Opportunity, Project, Site, Strategy
from .permissions import can_invite, can_manage_roles


class OpportunityTestCase(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='manager', email='manager@example.com', password='pw')
        self.delegate = User.objects.create_user(username='delegate', email='delegate@example.com', password='pw')
        self.stakeholder = User.objects.create_user(
            username='stakeholder', email='stakeholder@example.com', password='pw'
        )
        self.stranger = User.objects.create_user(username='stranger', email='stranger@example.com', password='pw')

        self.vru = FocusArea.objects.get(name='Vulnerable Road Users')
        self.lead_agency = Group.objects.create(name='Lead Agency', admin=self.manager)
        Membership.objects.create(user=self.manager, group=self.lead_agency)

        self.opportunity = Opportunity.objects.create(
            title='Test Opportunity',
            focus_area=self.vru,
            lead_agency=self.lead_agency,
            manager=self.manager,
        )
        self.opportunity.delegates.add(self.delegate)
        self.opportunity.stakeholders.add(self.stakeholder)


class OpportunityPermissionTests(OpportunityTestCase):
    def test_opportunity_list_includes_managing_agency_and_manager_names(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/opportunities/')

        self.assertEqual(response.data[0]['lead_agency_name'], 'Lead Agency')
        self.assertEqual(response.data[0]['manager_name'], 'manager')

    def test_manager_can_read_and_write(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(f'/api/opportunities/{self.opportunity.pk}/', {'title': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delegate_can_read_and_write(self):
        self.client.force_authenticate(user=self.delegate)
        response = self.client.patch(f'/api/opportunities/{self.opportunity.pk}/', {'title': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stakeholder_can_read_but_not_write(self):
        self.client.force_authenticate(user=self.stakeholder)
        read_response = self.client.get(f'/api/opportunities/{self.opportunity.pk}/')
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)

        write_response = self.client.patch(f'/api/opportunities/{self.opportunity.pk}/', {'title': 'Hacked'})
        self.assertEqual(write_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_cannot_read(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(f'/api/opportunities/{self.opportunity.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_opportunity_list_is_scoped_per_user(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get('/api/opportunities/')
        self.assertEqual(len(response.data), 0)

        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.get('/api/opportunities/')
        self.assertEqual(len(response.data), 1)

    def test_associated_agency_member_can_list_and_read_opportunity(self):
        associated_agency = Group.objects.create(name='Associated Agency', admin=self.manager)
        Membership.objects.create(user=self.stranger, group=associated_agency)
        self.opportunity.assoc_agencies.add(associated_agency)

        self.client.force_authenticate(user=self.stranger)
        list_response = self.client.get('/api/opportunities/')
        detail_response = self.client.get(f'/api/opportunities/{self.opportunity.pk}/')

        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]['id'], self.opportunity.pk)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get('/api/opportunities/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OpportunityCreationTests(OpportunityTestCase):
    def test_opportunity_status_uses_named_choices(self):
        self.assertEqual(self.opportunity.status, Opportunity.Status.DRAFTING)

        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/opportunities/{self.opportunity.pk}/', {'status': 'review'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'review')

    def test_opportunity_rejects_unknown_status(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/opportunities/{self.opportunity.pk}/', {'status': 'in_progress'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_create_opportunity_with_manager_who_is_lead_agency_member(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            '/api/opportunities/',
            {
                'title': 'New Opportunity',
                'comment': '',
                'focus_area': self.vru.pk,
                'lead_agency': self.lead_agency.pk,
                'manager': self.manager.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['manager'], self.manager.pk)

    def test_create_opportunity_with_manager_who_is_lead_agency_admin_but_not_a_member(self):
        # Regression test: a Group's admin is tracked via Group.admin, not a
        # Membership row, so they must be accepted as a valid manager even
        # with no separate Membership -- this is what broke Opportunity
        # creation (blank screen picking a lead agency) after Group Admin
        # shipped, since the admin-only case wasn't covered before.
        admin_only_group = Group.objects.create(name='Admin Only Agency', admin=self.stranger)
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(
            '/api/opportunities/',
            {
                'title': 'New Opportunity',
                'comment': '',
                'focus_area': self.vru.pk,
                'lead_agency': admin_only_group.pk,
                'manager': self.stranger.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['manager'], self.stranger.pk)

    def test_create_opportunity_with_manager_not_in_lead_agency_fails(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            '/api/opportunities/',
            {
                'title': 'New Opportunity',
                'comment': '',
                'focus_area': self.vru.pk,
                'lead_agency': self.lead_agency.pk,
                'manager': self.stranger.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('manager', response.data)


class OpportunityImmutabilityTests(OpportunityTestCase):
    def test_focus_area_immutable_after_creation(self):
        other_focus_area = FocusArea.objects.exclude(pk=self.vru.pk).first()
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/opportunities/{self.opportunity.pk}/', {'focus_area': other_focus_area.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('focus_area', response.data)

    def test_unrelated_field_still_writable(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(f'/api/opportunities/{self.opportunity.pk}/', {'title': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delegates_stakeholders_not_writable_via_plain_patch(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/opportunities/{self.opportunity.pk}/', {'delegates': [self.stranger.pk]}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.opportunity.delegates.filter(pk=self.stranger.pk).exists())


class MembershipPermissionTests(OpportunityTestCase):
    def test_only_manager_can_invite(self):
        self.assertTrue(can_invite(self.manager, self.opportunity))
        self.assertFalse(can_invite(self.delegate, self.opportunity))
        self.assertFalse(can_invite(self.stakeholder, self.opportunity))
        self.assertFalse(can_invite(self.stranger, self.opportunity))

    def test_only_manager_can_manage_roles(self):
        self.assertTrue(can_manage_roles(self.manager, self.opportunity))
        self.assertFalse(can_manage_roles(self.delegate, self.opportunity))
        self.assertFalse(can_manage_roles(self.stakeholder, self.opportunity))
        self.assertFalse(can_manage_roles(self.stranger, self.opportunity))


class MembershipEndpointTests(OpportunityTestCase):
    def members_url(self, opportunity=None):
        return f'/api/opportunities/{(opportunity or self.opportunity).pk}/members/'

    def member_detail_url(self, user, opportunity=None):
        return f'/api/opportunities/{(opportunity or self.opportunity).pk}/members/{user.pk}/'

    def invite_group_url(self, opportunity=None):
        return f'/api/opportunities/{(opportunity or self.opportunity).pk}/invite-group/'

    def test_manager_can_list_members(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roles = {member['username']: member['role'] for member in response.data}
        self.assertEqual(roles, {'manager': 'manager', 'delegate': 'delegate', 'stakeholder': 'stakeholder'})

    def test_stakeholder_can_list_members(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_list_members(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_invite_new_delegate(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            self.members_url(), {'identifier': self.stranger.username, 'role': 'delegate'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.opportunity.delegates.filter(pk=self.stranger.pk).exists())

    def test_manager_can_invite_by_email(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            self.members_url(), {'identifier': self.stranger.email, 'role': 'stakeholder'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.opportunity.stakeholders.filter(pk=self.stranger.pk).exists())

    def test_delegate_cannot_invite(self):
        self.client.force_authenticate(user=self.delegate)
        response = self.client.post(
            self.members_url(), {'identifier': self.stranger.username, 'role': 'delegate'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_nonexistent_user_fails(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.members_url(), {'identifier': 'nobody', 'role': 'delegate'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invite_existing_member_fails(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            self.members_url(), {'identifier': self.stakeholder.username, 'role': 'delegate'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invite_manager_fails(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            self.members_url(), {'identifier': self.manager.username, 'role': 'delegate'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_can_invite_group_adds_all_members_as_stakeholders(self):
        other_group = Group.objects.create(name='Other Group', admin=self.manager)
        second_stranger = User.objects.create_user(username='stranger2', email='stranger2@example.com', password='pw')
        Membership.objects.create(user=self.stranger, group=other_group)
        Membership.objects.create(user=second_stranger, group=other_group)

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.invite_group_url(), {'group_id': other_group.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.opportunity.stakeholders.filter(pk=self.stranger.pk).exists())
        self.assertTrue(self.opportunity.stakeholders.filter(pk=second_stranger.pk).exists())

    def test_invite_group_includes_subgroup_members(self):
        parent_group = Group.objects.create(name='Parent Group', admin=self.manager)
        child_group = Group.objects.create(name='Child Group', parent=parent_group, admin=self.manager)
        Membership.objects.create(user=self.stranger, group=child_group)

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.invite_group_url(), {'group_id': parent_group.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.opportunity.stakeholders.filter(pk=self.stranger.pk).exists())

    def test_invite_group_skips_existing_members_without_downgrading(self):
        other_group = Group.objects.create(name='Other Group', admin=self.manager)
        Membership.objects.create(user=self.delegate, group=other_group)
        Membership.objects.create(user=self.stranger, group=other_group)

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.invite_group_url(), {'group_id': other_group.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Already a delegate -- must not be downgraded to stakeholder.
        self.assertTrue(self.opportunity.delegates.filter(pk=self.delegate.pk).exists())
        self.assertFalse(self.opportunity.stakeholders.filter(pk=self.delegate.pk).exists())
        self.assertTrue(self.opportunity.stakeholders.filter(pk=self.stranger.pk).exists())

    def test_invite_group_with_no_new_members_fails(self):
        other_group = Group.objects.create(name='Other Group', admin=self.manager)
        Membership.objects.create(user=self.stakeholder, group=other_group)

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.invite_group_url(), {'group_id': other_group.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delegate_cannot_invite_group(self):
        other_group = Group.objects.create(name='Other Group', admin=self.manager)
        Membership.objects.create(user=self.stranger, group=other_group)

        self.client.force_authenticate(user=self.delegate)
        response = self.client.post(self.invite_group_url(), {'group_id': other_group.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_change_member_role(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(self.member_detail_url(self.stakeholder), {'role': 'delegate'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.opportunity.delegates.filter(pk=self.stakeholder.pk).exists())
        self.assertFalse(self.opportunity.stakeholders.filter(pk=self.stakeholder.pk).exists())

    def test_manager_can_promote_delegate_to_manager(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(self.member_detail_url(self.delegate), {'role': 'manager'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.manager_id, self.delegate.pk)
        self.assertTrue(self.opportunity.delegates.filter(pk=self.manager.pk).exists())

    def test_cannot_promote_stakeholder_directly_to_manager(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(self.member_detail_url(self.stakeholder), {'role': 'manager'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delegate_cannot_change_role(self):
        self.client.force_authenticate(user=self.delegate)
        response = self.client.patch(self.member_detail_url(self.stakeholder), {'role': 'delegate'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_role_for_non_member_is_not_found(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(self.member_detail_url(self.stranger), {'role': 'delegate'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_remove_member(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(self.member_detail_url(self.delegate))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.opportunity.delegates.filter(pk=self.delegate.pk).exists())

    def test_stakeholder_cannot_remove_member(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.delete(self.member_detail_url(self.delegate))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CloningTests(OpportunityTestCase):
    def test_clone_opportunity_copies_fields_and_adds_requester_as_delegate(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(f'/api/opportunities/{self.opportunity.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cloned_opportunity = Opportunity.objects.get(pk=response.data['id'])
        self.assertNotEqual(cloned_opportunity.pk, self.opportunity.pk)
        self.assertEqual(cloned_opportunity.title, f'{self.opportunity.title} (Copy)')
        self.assertEqual(cloned_opportunity.manager, self.manager)
        self.assertEqual(cloned_opportunity.lead_agency, self.lead_agency)
        self.assertEqual(cloned_opportunity.delegates.count(), 0)
        self.assertEqual(cloned_opportunity.stakeholders.count(), 0)

        # Original untouched.
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.title, 'Test Opportunity')

    def test_stakeholder_cloning_becomes_delegate_on_the_copy(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.post(f'/api/opportunities/{self.opportunity.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cloned_opportunity = Opportunity.objects.get(pk=response.data['id'])
        self.assertEqual(cloned_opportunity.manager, self.manager)
        self.assertTrue(cloned_opportunity.delegates.filter(pk=self.stakeholder.pk).exists())

    def test_stranger_cannot_clone_opportunity(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(f'/api/opportunities/{self.opportunity.pk}/clone/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HierarchyTestCase(OpportunityTestCase):
    """Covers the nested Project -> Site -> Strategy chain: creation, ancestor-scoped
    permissions, and get_opportunity() propagation at every level."""

    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(opportunity=self.opportunity, title='Test Project')
        self.site = Site.objects.create(project=self.project, title='Test Site')
        # Any InterventionType works for chain/permission tests that don't
        # care about focus-area compatibility.
        self.intervention_type = InterventionType.objects.first()
        self.strategy = Strategy.objects.create(site=self.site, intervention_type=self.intervention_type)

    def test_manager_can_create_project(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            f'/api/opportunities/{self.opportunity.pk}/projects/', {'title': 'New Project', 'comment': ''}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['opportunity'], self.opportunity.pk)

    def test_stakeholder_cannot_create_project(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.post(
            f'/api/opportunities/{self.opportunity.pk}/projects/', {'title': 'New Project', 'comment': ''}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_gets_404_listing_projects(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(f'/api/opportunities/{self.opportunity.pk}/projects/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delegate_can_create_site(self):
        self.client.force_authenticate(user=self.delegate)
        response = self.client.post(
            f'/api/projects/{self.project.pk}/sites/', {'title': 'New Site', 'comment': ''}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['project'], self.project.pk)

    def test_stakeholder_can_read_site_but_not_write(self):
        self.client.force_authenticate(user=self.stakeholder)
        read_response = self.client.get(f'/api/sites/{self.site.pk}/')
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)

        write_response = self.client.patch(f'/api/sites/{self.site.pk}/', {'title': 'Hacked'})
        self.assertEqual(write_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_create_strategy_via_nested_route(self):
        # Strategy rows are auto-provisioned (see StrategyProvisioningTestCase),
        # never user-created -- the nested route only maps GET.
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            f'/api/sites/{self.site.pk}/strategies/', {'intervention_type': self.intervention_type.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cannot_create_strategy_via_flat_route(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/strategies/', {'intervention_type': self.intervention_type.pk})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cannot_delete_strategy(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(f'/api/strategies/{self.strategy.pk}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_stranger_gets_404_on_deeply_nested_strategy(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(f'/api/strategies/{self.strategy.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_opportunity_chain_is_correct(self):
        self.assertEqual(self.project.get_opportunity(), self.opportunity)
        self.assertEqual(self.site.get_opportunity(), self.opportunity)
        self.assertEqual(self.strategy.get_opportunity(), self.opportunity)

    def test_casualty_arrays_default_to_25_zero_values(self):
        self.assertEqual(self.site.casualty_obs, [0] * 25)
        self.assertEqual(self.site.casualty_est, [0] * 25)
        self.assertEqual(self.site.casualty_data_type, 'casualty-damage')
        self.assertEqual(self.site.casualty_time_years, 1)
        self.assertEqual(self.site.casualty_time_months, 1)

    def test_casualty_array_wrong_length_rejected(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(f'/api/sites/{self.site.pk}/', {'casualty_obs': [1] * 24}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('casualty_obs', response.data)

    def test_casualty_array_negative_value_rejected(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/sites/{self.site.pk}/', {'casualty_obs': [1] * 24 + [-1]}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('casualty_obs', response.data)

    def test_casualty_array_valid_update_succeeds(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/sites/{self.site.pk}/', {'casualty_obs': list(range(1, 26))}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['casualty_obs'], list(range(1, 26)))

    def test_casualty_data_type_can_be_updated(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/sites/{self.site.pk}/', {'casualty_data_type': 'crash'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['casualty_data_type'], 'crash')

    def test_casualty_time_bracket_ranges_are_enforced(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/sites/{self.site.pk}/',
            {'casualty_time_years': 26, 'casualty_time_months': 12},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('casualty_time_years', response.data)
        self.assertIn('casualty_time_months', response.data)

    def test_manager_can_assign_one_site_jcode_and_remove_it(self):
        jcode = Jcode.objects.create(
            id='0400100',
            state='Arizona',
            county='Maricopa',
            place_name_short='Phoenix',
            place_name_long='Phoenix city',
        )
        self.lead_agency.jcodes.add(jcode)

        self.client.force_authenticate(user=self.manager)
        assign_response = self.client.patch(
            f'/api/sites/{self.site.pk}/', {'jcode_id': jcode.pk}, format='json'
        )
        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)
        self.assertEqual(assign_response.data['jcode']['id'], jcode.pk)

        remove_response = self.client.patch(
            f'/api/sites/{self.site.pk}/', {'jcode_id': None}, format='json'
        )
        self.assertEqual(remove_response.status_code, status.HTTP_200_OK)
        self.assertIsNone(remove_response.data['jcode'])

    def test_site_cannot_use_jcode_outside_lead_agency_access(self):
        jcode = Jcode.objects.create(
            id='0400100',
            state='Arizona',
            county='Maricopa',
            place_name_short='Phoenix',
            place_name_long='Phoenix city',
        )

        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/sites/{self.site.pk}/', {'jcode_id': jcode.pk}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('jcode_id', response.data)

    def test_available_site_jcodes_are_limited_to_lead_agency(self):
        available = Jcode.objects.create(
            id='0400100', state='Arizona', county='Maricopa', place_name_short='Phoenix', place_name_long='Phoenix city'
        )
        unavailable = Jcode.objects.create(
            id='0600100', state='California', county='Los Angeles', place_name_short='LA', place_name_long='Los Angeles city'
        )
        self.lead_agency.jcodes.add(available)

        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f'/api/sites/{self.site.pk}/available-jcodes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row['id'] for row in response.data], [available.pk])
        self.assertNotIn(unavailable.pk, [row['id'] for row in response.data])

    def test_assigning_a_second_site_jcode_replaces_the_first(self):
        first = Jcode.objects.create(
            id='0400100', state='Arizona', county='Maricopa', place_name_short='Phoenix', place_name_long='Phoenix city'
        )
        second = Jcode.objects.create(
            id='0600100', state='California', county='Los Angeles', place_name_short='LA', place_name_long='Los Angeles city'
        )
        self.lead_agency.jcodes.add(first, second)

        self.client.force_authenticate(user=self.manager)
        self.client.patch(f'/api/sites/{self.site.pk}/', {'jcode_id': first.pk}, format='json')
        response = self.client.patch(f'/api/sites/{self.site.pk}/', {'jcode_id': second.pk}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['jcode']['id'], second.pk)
        self.site.refresh_from_db()
        self.assertEqual(self.site.jcode_id, second.pk)

    def test_deleting_opportunity_cascades_through_hierarchy(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(f'/api/opportunities/{self.opportunity.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(Site.objects.filter(pk=self.site.pk).exists())
        self.assertFalse(Strategy.objects.filter(pk=self.strategy.pk).exists())


class CommentsEnabledToggleTests(HierarchyTestCase):
    def toggle_url(self, project=None):
        return f'/api/projects/{(project or self.project).pk}/comments-enabled/'

    def test_comments_enabled_defaults_true(self):
        self.assertTrue(self.project.comments_enabled)

    def test_manager_can_disable_and_re_enable_comments(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(self.toggle_url(), {'comments_enabled': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['comments_enabled'])
        self.project.refresh_from_db()
        self.assertFalse(self.project.comments_enabled)

        response = self.client.patch(self.toggle_url(), {'comments_enabled': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['comments_enabled'])

    def test_delegate_cannot_toggle_comments_enabled(self):
        self.client.force_authenticate(user=self.delegate)
        response = self.client.patch(self.toggle_url(), {'comments_enabled': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stakeholder_cannot_toggle_comments_enabled(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.patch(self.toggle_url(), {'comments_enabled': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_comments_enabled_not_writable_via_plain_patch(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(f'/api/projects/{self.project.pk}/', {'comments_enabled': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertTrue(self.project.comments_enabled)


class StrategyProvisioningTestCase(OpportunityTestCase):
    """
    Strategy rows are auto-provisioned per Site for every InterventionType
    compatible with the Opportunity's focus area (Site.sync_strategies),
    never created/deleted by users -- only `selected` (the checkbox) and
    `details` (placeholder JSON) are ever written.
    """

    def setUp(self):
        super().setUp()
        self.pedestrians = FocusArea.objects.get(name='Pedestrians')
        self.opportunity.specific_focus_area = self.pedestrians
        self.opportunity.save(update_fields=['specific_focus_area'])
        self.project = Project.objects.create(opportunity=self.opportunity, title='Test Project')
        self.site = Site.objects.create(project=self.project, title='Test Site')
        self.compatible_count = InterventionType.objects.filter(
            focus_areas=self.pedestrians, is_active=True
        ).count()
        self.assertGreater(self.compatible_count, 0, 'fixture assumption: Pedestrians has compatible types')

    def strategies_url(self):
        return f'/api/sites/{self.site.pk}/strategies/'

    def test_listing_strategies_auto_provisions_compatible_intervention_types(self):
        self.assertEqual(Strategy.objects.filter(site=self.site).count(), 0)

        self.client.force_authenticate(user=self.manager)
        response = self.client.get(self.strategies_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), self.compatible_count)
        self.assertTrue(all(row['selected'] is False for row in response.data))
        self.assertTrue(all(row['details'] == {} for row in response.data))
        self.assertEqual(Strategy.objects.filter(site=self.site).count(), self.compatible_count)

    def test_strategy_exposes_the_intervention_cmf(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(self.strategies_url())

        rrfb = next(
            row for row in response.data
            if row['intervention_type']['name'] == 'Rectangular Rapid Flashing Beacons (RRFBs)'
        )
        self.assertEqual(rrfb['intervention_type']['cmf']['code'], 'cmf-rrfb')
        self.assertEqual(rrfb['intervention_type']['cmf']['coefficient_array'][3][0][1], 0.75)

    def test_sync_is_idempotent_and_preserves_existing_state(self):
        self.site.sync_strategies()
        strategy = self.site.strategies.first()
        strategy.selected = True
        strategy.details = {'note': 'kept'}
        strategy.save(update_fields=['selected', 'details'])

        self.site.sync_strategies()
        self.assertEqual(Strategy.objects.filter(site=self.site).count(), self.compatible_count)
        strategy.refresh_from_db()
        self.assertTrue(strategy.selected)
        self.assertEqual(strategy.details, {'note': 'kept'})

    def test_stakeholder_can_list_strategies(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.get(self.strategies_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), self.compatible_count)

    def test_stranger_gets_404_listing_strategies(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(self.strategies_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_toggle_selected(self):
        self.site.sync_strategies()
        strategy = self.site.strategies.first()

        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(f'/api/strategies/{strategy.pk}/', {'selected': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['selected'])
        strategy.refresh_from_db()
        self.assertTrue(strategy.selected)

    def test_stakeholder_cannot_toggle_selected(self):
        self.site.sync_strategies()
        strategy = self.site.strategies.first()

        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.patch(f'/api/strategies/{strategy.pk}/', {'selected': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_edit_details(self):
        self.site.sync_strategies()
        strategy = self.site.strategies.first()

        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/strategies/{strategy.pk}/', {'details': {'anything': 'goes'}}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['details'], {'anything': 'goes'})

    def test_details_must_be_a_json_object(self):
        self.site.sync_strategies()
        strategy = self.site.strategies.first()

        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/strategies/{strategy.pk}/', {'details': ['not', 'an', 'object']}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)

    def test_intervention_type_is_not_writable(self):
        self.site.sync_strategies()
        strategies = list(self.site.strategies.all()[:2])
        strategy, other = strategies[0], strategies[1]

        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f'/api/strategies/{strategy.pk}/', {'intervention_type': other.intervention_type_id}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        strategy.refresh_from_db()
        self.assertNotEqual(strategy.intervention_type_id, other.intervention_type_id)
