from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from geo.models import Jcode

from .models import Group, Membership


class GroupsTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', email='admin@example.com', password='pw')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='pw')

    def members_url(self, group):
        return f'/api/groups/{group.pk}/members/'

    def member_detail_url(self, group, user):
        return f'/api/groups/{group.pk}/members/{user.pk}/'

    def set_admin_url(self, group):
        return f'/api/groups/{group.pk}/set-admin/'


class GroupCrudTests(GroupsTestCase):
    def test_mine_lists_only_groups_the_user_belongs_to_with_role(self):
        admin_group = Group.objects.create(name='Admin group', admin=self.admin)
        member_group = Group.objects.create(name='Member group', admin=self.other)
        Group.objects.create(name='Unrelated group', admin=self.other)
        Membership.objects.create(user=self.admin, group=member_group)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/groups/mine/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {group['name']: group['user_role'] for group in response.data},
            {'Admin group': 'admin', 'Member group': 'member'},
        )

    def test_admin_can_replace_group_jcodes(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        first = Jcode.objects.create(id='0400100', state='Arizona', county='Maricopa', place_name_short='Phoenix', place_name_long='Phoenix city')
        second = Jcode.objects.create(id='0600100', state='California', county='Los Angeles', place_name_short='LA', place_name_long='Los Angeles city')
        group.jcodes.add(first)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/groups/{group.pk}/jcodes/', {'jcode_ids': [second.pk]}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(group.jcodes.values_list('id', flat=True)), ['0600100'])
        self.assertEqual([jcode['id'] for jcode in response.data['jcodes']], ['0600100'])

    def test_non_admin_cannot_replace_group_jcodes(self):
        group = Group.objects.create(name='Agency', admin=self.other)
        jcode = Jcode.objects.create(id='0400100', state='Arizona', county='Maricopa', place_name_short='Phoenix', place_name_long='Phoenix city')

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/groups/{group.pk}/jcodes/', {'jcode_ids': [jcode.pk]}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_becomes_admin_on_create(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/groups/', {'name': 'Acme DOT'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Acme DOT')
        self.assertIsNone(response.data['parent'])
        self.assertEqual(response.data['admin']['id'], self.admin.pk)
        # effective_members (the transitive "members" field) counts the
        # admin too -- they're a real member of their own group, just not
        # via a Membership row.
        self.assertEqual([m['id'] for m in response.data['members']], [self.admin.pk])

    def test_admin_can_create_subgroup_and_becomes_its_admin(self):
        parent = Group.objects.create(name='Acme DOT', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/groups/', {'name': 'Traffic Engineering', 'parent': parent.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['parent'], parent.pk)
        self.assertEqual(response.data['admin']['id'], self.admin.pk)

    def test_non_admin_cannot_create_subgroup(self):
        parent = Group.objects.create(name='Acme DOT', admin=self.other)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/groups/', {'name': 'Traffic Engineering', 'parent': parent.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_name_unique_per_parent_not_globally(self):
        parent_a = Group.objects.create(name='Org A', admin=self.admin)
        parent_b = Group.objects.create(name='Org B', admin=self.admin)
        Group.objects.create(name='Finance', parent=parent_a, admin=self.admin)

        self.client.force_authenticate(user=self.admin)
        # Same name under a different parent is fine.
        response = self.client.post('/api/groups/', {'name': 'Finance', 'parent': parent_b.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Same name under the same parent is rejected.
        response = self.client.post('/api/groups/', {'name': 'Finance', 'parent': parent_a.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_groups_by_name(self):
        Group.objects.create(name='City of Raleigh DOT', admin=self.admin)
        Group.objects.create(name='NCDOT', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/groups/', {'q': 'raleigh'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'City of Raleigh DOT')

    def test_deleting_group_cascades_to_subgroups(self):
        parent = Group.objects.create(name='Parent', admin=self.admin)
        child = Group.objects.create(name='Child', parent=parent, admin=self.admin)

        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/groups/{parent.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(pk=child.pk).exists())

    def test_non_admin_cannot_update_group(self):
        group = Group.objects.create(name='Parent', admin=self.other)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/groups/{group.pk}/', {'name': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_delete_group(self):
        group = Group.objects.create(name='Parent', admin=self.other)
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/groups/{group.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_group(self):
        group = Group.objects.create(name='Parent', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/groups/{group.pk}/', {'name': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Renamed')


class GroupCycleTests(GroupsTestCase):
    def test_cannot_reparent_group_to_create_a_cycle(self):
        a = Group.objects.create(name='A', admin=self.admin)
        b = Group.objects.create(name='B', parent=a, admin=self.admin)
        c = Group.objects.create(name='C', parent=b, admin=self.admin)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/groups/{a.pk}/', {'parent': c.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_group_cannot_be_its_own_parent(self):
        a = Group.objects.create(name='A', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/groups/{a.pk}/', {'parent': a.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unrelated_reparenting_is_allowed_when_admin_of_both(self):
        a = Group.objects.create(name='A', admin=self.admin)
        b = Group.objects.create(name='B', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/groups/{b.pk}/', {'parent': a.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reparenting_requires_admin_of_new_parent(self):
        a = Group.objects.create(name='A', admin=self.other)
        b = Group.objects.create(name='B', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/groups/{b.pk}/', {'parent': a.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent', response.data)


class EffectiveMembersTests(GroupsTestCase):
    def test_member_of_subgroup_counts_as_member_of_parent(self):
        parent_admin = User.objects.create_user(username='parent_admin', email='pa@example.com', password='pw')
        child_admin = User.objects.create_user(username='child_admin', email='ca@example.com', password='pw')
        grandchild_admin = User.objects.create_user(
            username='grandchild_admin', email='ga@example.com', password='pw'
        )
        parent = Group.objects.create(name='Agency', admin=parent_admin)
        child = Group.objects.create(name='Department', parent=parent, admin=child_admin)
        grandchild = Group.objects.create(name='Team', parent=child, admin=grandchild_admin)

        Membership.objects.create(user=self.admin, group=parent, roles=['Director'])
        Membership.objects.create(user=self.other, group=grandchild, roles=['Analyst'])

        # Each level's admin counts as a member of that level and everything
        # above it (they're a real member, just via the `admin` FK rather
        # than a Membership row); a group's own admin never leaks *down* into
        # a subgroup's effective membership though.
        parent_member_ids = {u.pk for u in parent.effective_members()}
        self.assertEqual(
            parent_member_ids,
            {parent_admin.pk, child_admin.pk, grandchild_admin.pk, self.admin.pk, self.other.pk},
        )

        child_member_ids = {u.pk for u in child.effective_members()}
        self.assertEqual(child_member_ids, {child_admin.pk, grandchild_admin.pk, self.other.pk})

    def test_member_of_two_subgroups_is_not_duplicated(self):
        parent = Group.objects.create(name='Agency', admin=self.admin)
        child_a = Group.objects.create(name='A', parent=parent, admin=self.admin)
        child_b = Group.objects.create(name='B', parent=parent, admin=self.admin)
        Membership.objects.create(user=self.other, group=child_a)
        Membership.objects.create(user=self.other, group=child_b)

        # self.admin administers all three groups in this hierarchy, so they
        # count as an effective member too, deduplicated across all of them.
        self.assertEqual(list(parent.effective_members()), [self.admin, self.other])


class MembershipTests(GroupsTestCase):
    # Membership-creation tests (invite, request-to-join, accept/decline)
    # live in notifications/tests.py -- Memberships are no longer created
    # directly via this app's API, only via NotificationViewSet.accept.

    def test_membership_db_constraint(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        Membership.objects.create(user=self.other, group=group)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(user=self.other, group=group)

    def test_admin_can_update_member_roles(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        Membership.objects.create(user=self.other, group=group, roles=['Analyst'])

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            self.member_detail_url(group, self.other), {'roles': ['Analyst', 'Lead']}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = Membership.objects.get(group=group, user=self.other)
        self.assertEqual(membership.roles, ['Analyst', 'Lead'])

    def test_non_admin_cannot_update_member_roles(self):
        group = Group.objects.create(name='Agency', admin=self.other)
        Membership.objects.create(user=self.admin, group=group)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            self.member_detail_url(group, self.admin), {'roles': ['Lead']}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_remove_member(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        Membership.objects.create(user=self.other, group=group)

        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(self.member_detail_url(group, self.other))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Membership.objects.filter(group=group, user=self.other).exists())

    def test_non_admin_cannot_remove_member(self):
        group = Group.objects.create(name='Agency', admin=self.other)
        Membership.objects.create(user=self.admin, group=group)

        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(self.member_detail_url(group, self.admin))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_members_includes_admin_and_direct_members_only(self):
        parent = Group.objects.create(name='Agency', admin=self.admin)
        child = Group.objects.create(name='Team', parent=parent, admin=self.admin)
        Membership.objects.create(user=self.other, group=parent)
        child_member = User.objects.create_user(username='childmember', email='cm@example.com', password='pw')
        Membership.objects.create(user=child_member, group=child)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.members_url(parent))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        roles_by_username = {row['username']: row['role'] for row in response.data}
        self.assertEqual(roles_by_username, {'admin': 'admin', 'other': 'member'})


class SetAdminTests(GroupsTestCase):
    def test_admin_can_promote_a_member(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        Membership.objects.create(user=self.other, group=group, roles=['Analyst'])

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.set_admin_url(group), {'user_id': self.other.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        group.refresh_from_db()
        self.assertEqual(group.admin_id, self.other.pk)
        # The promoted member's Membership row is gone (admin is tracked via the FK, not Membership)...
        self.assertFalse(Membership.objects.filter(group=group, user=self.other).exists())
        # ...and the outgoing admin becomes a regular member instead of losing access.
        self.assertTrue(Membership.objects.filter(group=group, user=self.admin).exists())

    def test_target_must_be_a_current_member(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.set_admin_url(group), {'user_id': self.other.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_admin_cannot_reassign_admin(self):
        group = Group.objects.create(name='Agency', admin=self.other)
        Membership.objects.create(user=self.admin, group=group)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.set_admin_url(group), {'user_id': self.admin.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
