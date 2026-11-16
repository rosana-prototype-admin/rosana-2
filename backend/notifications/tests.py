from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from groups.models import Group, Membership

from .models import Notification


class NotificationsTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', email='admin@example.com', password='pw')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='pw')

    def invite_url(self, group):
        return f'/api/groups/{group.pk}/invite/'

    def request_to_join_url(self, group):
        return f'/api/groups/{group.pk}/request-to-join/'

    def accept_url(self, notification):
        return f'/api/notifications/{notification.pk}/accept/'

    def decline_url(self, notification):
        return f'/api/notifications/{notification.pk}/decline/'

    def cancel_url(self, notification):
        return f'/api/notifications/{notification.pk}/cancel/'

    def notifications_url(self):
        return '/api/notifications/'


class GroupInviteTests(NotificationsTestCase):
    def test_admin_can_invite_creates_pending_notification_not_membership(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self.invite_url(group), {'user_id': self.other.pk, 'organizational_roles': ['Coordinator']}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['notification_type'], 'group_invite')
        self.assertEqual(response.data['status'], 'pending')
        self.assertFalse(Membership.objects.filter(group=group, user=self.other).exists())
        notification = Notification.objects.get(group=group, user=self.other)
        self.assertEqual(notification.roles, ['Coordinator'])

    def test_invite_permissions_are_copied_when_accepted(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        requested_permissions = {'comment_existing_resources': True, 'create_modify_project': True}
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self.invite_url(group),
            {
                'user_id': self.other.pk,
                'organizational_roles': ['Analyst'],
                'permissions': requested_permissions,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(group=group, user=self.other)
        self.assertTrue(notification.permissions['comment_existing_resources'])

        self.client.force_authenticate(user=self.other)
        self.client.post(self.accept_url(notification))
        membership = Membership.objects.get(group=group, user=self.other)
        self.assertEqual(membership.permissions['comment_existing_resources'], True)
        self.assertEqual(membership.permissions['create_modify_project'], True)
        self.assertEqual(membership.permissions['delete_project'], False)

    def test_member_with_add_and_change_permissions_can_invite(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        inviter = User.objects.create_user(username='inviter', email='inviter@example.com', password='pw')
        invitee = User.objects.create_user(username='invitee', email='invitee@example.com', password='pw')
        Membership.objects.create(
            user=inviter,
            group=group,
            permissions={'add_new_user': True, 'change_user_permissions': True},
        )
        self.client.force_authenticate(user=inviter)
        response = self.client.post(
            self.invite_url(group),
            {'user_id': invitee.pk, 'permissions': {'comment_existing_resources': True}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_member_without_change_permission_cannot_assign_permissions(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        inviter = User.objects.create_user(username='inviter', email='inviter@example.com', password='pw')
        invitee = User.objects.create_user(username='invitee', email='invitee@example.com', password='pw')
        Membership.objects.create(user=inviter, group=group, permissions={'add_new_user': True})
        self.client.force_authenticate(user=inviter)
        response = self.client.post(
            self.invite_url(group),
            {'user_id': invitee.pk, 'permissions': {'comment_existing_resources': True}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_invite(self):
        group = Group.objects.create(name='Agency', admin=self.other)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.invite_url(group), {'user_id': self.admin.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inviting_the_group_admin_fails(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.invite_url(group), {'user_id': self.admin.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inviting_an_existing_member_fails(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        Membership.objects.create(user=self.other, group=group)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_pending_invite_is_rejected(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        first = self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_roles_must_be_a_list_of_strings(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.invite_url(group), {'user_id': self.other.pk, 'organizational_roles': 'Coordinator'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            self.invite_url(group), {'user_id': self.other.pk, 'organizational_roles': [1, 2]}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_child_group_invite_requires_parent_membership(self):
        parent = Group.objects.create(name='Agency', admin=self.admin)
        child = Group.objects.create(name='Team', parent=parent, admin=self.admin)
        self.client.force_authenticate(user=self.admin)

        # self.other is not (yet) a member of the parent -- rejected.
        response = self.client.post(self.invite_url(child), {'user_id': self.other.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Once they're a direct member of the parent, inviting them to the child works.
        Membership.objects.create(user=self.other, group=parent)
        response = self.client.post(self.invite_url(child), {'user_id': self.other.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class GroupJoinRequestTests(NotificationsTestCase):
    def test_user_can_request_to_join_creates_pending_notification(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        response = self.client.post(self.request_to_join_url(group))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['notification_type'], 'group_join_request')
        self.assertEqual(response.data['status'], 'pending')
        self.assertFalse(Membership.objects.filter(group=group, user=self.other).exists())

    def test_admin_cannot_request_to_join_own_group(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.request_to_join_url(group))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_member_cannot_request_to_join(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        Membership.objects.create(user=self.other, group=group)
        self.client.force_authenticate(user=self.other)
        response = self.client.post(self.request_to_join_url(group))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_pending_request_is_rejected(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        first = self.client.post(self.request_to_join_url(group))
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(self.request_to_join_url(group))
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requesting_to_join_a_subgroup_requires_parent_membership(self):
        parent = Group.objects.create(name='Agency', admin=self.admin)
        child = Group.objects.create(name='Team', parent=parent, admin=self.admin)
        self.client.force_authenticate(user=self.other)

        # Not (yet) a member of the parent -- rejected.
        response = self.client.post(self.request_to_join_url(child))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Once a direct member of the parent, requesting to join the child works.
        Membership.objects.create(user=self.other, group=parent)
        response = self.client.post(self.request_to_join_url(child))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class NotificationAcceptDeclineTests(NotificationsTestCase):
    def test_requester_can_see_and_cancel_their_pending_join_request(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=self.other)

        response = self.client.get(self.notifications_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['is_requester'])

        response = self.client.post(self.cancel_url(notification))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'canceled')
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.CANCELED)

    def test_requester_cannot_accept_or_decline_their_own_join_request(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=self.other)

        self.assertEqual(self.client.post(self.accept_url(notification)).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(self.decline_url(notification)).status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_requester_can_cancel_join_request(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=self.other)

        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.post(self.cancel_url(notification)).status_code, status.HTTP_404_NOT_FOUND)

    def test_invitee_can_accept_invite_creating_membership_with_roles(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        self.client.post(self.invite_url(group), {'user_id': self.other.pk, 'organizational_roles': ['Analyst']}, format='json')
        notification = Notification.objects.get(group=group, user=self.other)

        self.client.force_authenticate(user=self.other)
        response = self.client.post(self.accept_url(notification))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')

        membership = Membership.objects.get(group=group, user=self.other)
        self.assertEqual(membership.roles, ['Analyst'])

    def test_invitee_can_decline_invite_no_membership_created(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')
        notification = Notification.objects.get(group=group, user=self.other)

        self.client.force_authenticate(user=self.other)
        response = self.client.post(self.decline_url(notification))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'declined')
        self.assertFalse(Membership.objects.filter(group=group, user=self.other).exists())

    def test_only_invitee_can_accept_or_decline_their_invite(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')
        notification = Notification.objects.get(group=group, user=self.other)

        # The admin who sent it is not the recipient -- get_queryset() scopes
        # this notification away from them entirely (404, not 403).
        response = self.client.post(self.accept_url(notification))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_accept_join_request_creating_membership(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=self.other)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.accept_url(notification))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = Membership.objects.get(group=group, user=self.other)
        # Join requests never carry roles.
        self.assertEqual(membership.roles, [])
        self.assertFalse(any(membership.permissions.values()))

    def test_member_with_approve_permission_can_accept_join_request(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        approver = User.objects.create_user(username='approver', email='approver@example.com', password='pw')
        requester = User.objects.create_user(username='requester', email='requester@example.com', password='pw')
        Membership.objects.create(user=approver, group=group, permissions={'approve_new_user': True})
        self.client.force_authenticate(user=requester)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=requester)

        self.client.force_authenticate(user=approver)
        response = self.client.post(self.accept_url(notification))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = Membership.objects.get(group=group, user=requester)
        self.assertFalse(any(membership.permissions.values()))

    def test_admin_can_decline_join_request(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=self.other)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.decline_url(notification))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Membership.objects.filter(group=group, user=self.other).exists())

    def test_non_admin_cannot_act_on_join_request(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=self.other)

        # self.other can see their own request, but cannot approve it.
        response = self.client.post(self.accept_url(notification))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_request_recipient_follows_admin_reassignment(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        Membership.objects.create(user=self.other, group=group)
        new_admin = User.objects.create_user(username='newadmin', email='newadmin@example.com', password='pw')
        Membership.objects.create(user=new_admin, group=group)

        requester = User.objects.create_user(username='requester', email='req@example.com', password='pw')
        self.client.force_authenticate(user=requester)
        self.client.post(self.request_to_join_url(group))
        notification = Notification.objects.get(group=group, user=requester)

        # Reassign the group admin after the join request was created.
        self.client.force_authenticate(user=self.admin)
        self.client.post(f'/api/groups/{group.pk}/set-admin/', {'user_id': new_admin.pk}, format='json')

        # The old admin no longer sees it; the new admin does.
        self.client.force_authenticate(user=self.admin)
        stale_response = self.client.post(self.accept_url(notification))
        self.assertEqual(stale_response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=new_admin)
        response = self.client.post(self.accept_url(notification))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_accepting_an_already_resolved_notification_fails(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')
        notification = Notification.objects.get(group=group, user=self.other)

        self.client.force_authenticate(user=self.other)
        self.client.post(self.decline_url(notification))

        response = self.client.post(self.accept_url(notification))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_revalidates_membership_state_for_stale_duplicate_notifications(self):
        group = Group.objects.create(name='Agency', admin=self.admin)

        # Both an invite and a join request end up pending for the same user.
        self.client.force_authenticate(user=self.admin)
        self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')
        invite = Notification.objects.get(group=group, user=self.other, notification_type='group_invite')

        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(group))
        join_request = Notification.objects.get(group=group, user=self.other, notification_type='group_join_request')

        # Accept the join request first (as the admin) -- the user is now a member.
        self.client.force_authenticate(user=self.admin)
        accept_response = self.client.post(self.accept_url(join_request))
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)

        # The still-pending invite can no longer be accepted -- re-validation
        # at accept time catches the now-stale state.
        self.client.force_authenticate(user=self.other)
        stale_response = self.client.post(self.accept_url(invite))
        self.assertEqual(stale_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_notification_list_only_shows_my_actionable_notifications(self):
        group = Group.objects.create(name='Agency', admin=self.admin)
        self.client.force_authenticate(user=self.admin)
        self.client.post(self.invite_url(group), {'user_id': self.other.pk}, format='json')

        stranger = User.objects.create_user(username='stranger', email='stranger@example.com', password='pw')
        self.client.force_authenticate(user=stranger)
        response = self.client.get(self.notifications_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.notifications_url())
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['notification_type'], 'group_invite')

        # The admin sees join requests addressed to their group, not the
        # invite they themselves sent (they're not its recipient).
        self.client.force_authenticate(user=self.other)
        self.client.post(self.request_to_join_url(Group.objects.create(name='Other Agency', admin=stranger)))

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.notifications_url())
        self.assertEqual(len(response.data), 0)
