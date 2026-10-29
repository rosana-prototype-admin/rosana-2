from django.db import IntegrityError, transaction
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from focusareas.models import FocusArea
from groups.models import Group, Membership
from projects.models import Opportunity, Project

from .models import Comment, CommentVote


class DiscussionsTestCase(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='manager', email='manager@example.com', password='pw')
        self.delegate = User.objects.create_user(username='delegate', email='delegate@example.com', password='pw')
        self.stakeholder = User.objects.create_user(
            username='stakeholder', email='stakeholder@example.com', password='pw'
        )
        self.stranger = User.objects.create_user(username='stranger', email='stranger@example.com', password='pw')

        focus_area = FocusArea.objects.get(name='Vulnerable Road Users')
        lead_agency = Group.objects.create(name='Lead Agency', admin=self.manager)
        Membership.objects.create(user=self.manager, group=lead_agency)

        self.opportunity = Opportunity.objects.create(
            title='Test Opportunity', focus_area=focus_area, lead_agency=lead_agency, manager=self.manager
        )
        self.opportunity.delegates.add(self.delegate)
        self.opportunity.stakeholders.add(self.stakeholder)
        self.project = Project.objects.create(opportunity=self.opportunity, title='Test Project')

    def comments_url(self, project=None):
        return f'/api/projects/{(project or self.project).pk}/comments/'

    def comment_detail_url(self, comment):
        return f'/api/comments/{comment.pk}/'

    def vote_url(self, comment):
        return f'/api/comments/{comment.pk}/vote/'

    def delete_tree_url(self, comment):
        return f'/api/comments/{comment.pk}/delete-tree/'


class CommentRoleTests(DiscussionsTestCase):
    def test_manager_can_post_comment(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delegate_can_post_comment(self):
        self.client.force_authenticate(user=self.delegate)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_stakeholder_can_post_comment(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author']['id'], self.stakeholder.pk)

    def test_stranger_cannot_post_comment(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_delegate_stakeholder_can_read_comments(self):
        Comment.objects.create(project=self.project, author=self.manager, body='Hi')
        for user in (self.manager, self.delegate, self.stakeholder):
            self.client.force_authenticate(user=user)
            response = self.client.get(self.comments_url())
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)

    def test_stranger_cannot_read_comments(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(self.comments_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comment_must_be_created_via_nested_route(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/comments/', {'body': 'Flat create'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comment_body_at_max_length_is_accepted(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.comments_url(), {'body': 'x' * 2000})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_comment_body_over_max_length_is_rejected(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.comments_url(), {'body': 'x' * 2001})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CommentThreadingTests(DiscussionsTestCase):
    def test_reply_created_with_correct_parent_and_depth(self):
        root = Comment.objects.create(project=self.project, author=self.manager, body='Root')
        self.client.force_authenticate(user=self.delegate)
        response = self.client.post(self.comments_url(), {'body': 'Reply', 'parent': root.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['parent'], root.pk)
        self.assertEqual(response.data['depth'], 1)

    def test_reply_rejected_when_parent_belongs_to_different_project(self):
        other_project = Project.objects.create(opportunity=self.opportunity, title='Other Project')
        other_root = Comment.objects.create(project=other_project, author=self.manager, body='Root')

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.comments_url(), {'body': 'Reply', 'parent': other_root.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reply_up_to_max_depth_is_accepted_past_is_rejected(self):
        self.client.force_authenticate(user=self.manager)
        comment = Comment.objects.create(project=self.project, author=self.manager, body='Depth 0')
        for expected_depth in range(1, Comment.MAX_DEPTH + 1):
            response = self.client.post(self.comments_url(), {'body': f'Depth {expected_depth}', 'parent': comment.pk})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['depth'], expected_depth)
            comment = Comment.objects.get(pk=response.data['id'])

        response = self.client.post(self.comments_url(), {'body': 'Too deep', 'parent': comment.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CommentEditDeleteTests(DiscussionsTestCase):
    def test_author_can_edit_own_comment(self):
        comment = Comment.objects.create(project=self.project, author=self.delegate, body='Original')
        self.client.force_authenticate(user=self.delegate)
        response = self.client.patch(self.comment_detail_url(comment), {'body': 'Edited'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['body'], 'Edited')

    def test_non_author_cannot_edit_comment(self):
        comment = Comment.objects.create(project=self.project, author=self.delegate, body='Original')
        # Manager and delegate-of-the-opportunity both pass can_write/can_read
        # but are NOT the comment's author, so they must still be rejected --
        # this is what would catch an accidental fallback to can_write semantics.
        for user in (self.manager, self.stakeholder):
            self.client.force_authenticate(user=user)
            response = self.client.patch(self.comment_detail_url(comment), {'body': 'Hacked'})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editing_comment_over_max_length_is_rejected(self):
        comment = Comment.objects.create(project=self.project, author=self.delegate, body='Original')
        self.client.force_authenticate(user=self.delegate)
        response = self.client.patch(self.comment_detail_url(comment), {'body': 'x' * 2001})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_author_can_delete_own_comment_soft_deletes(self):
        comment = Comment.objects.create(project=self.project, author=self.stakeholder, body='Original')
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.delete(self.comment_detail_url(comment))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        comment.refresh_from_db()
        self.assertIsNotNone(comment.deleted_at)
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

    def test_deleting_comment_preserves_replies_and_tombstones_body(self):
        parent = Comment.objects.create(project=self.project, author=self.manager, body='Parent')
        reply = Comment.objects.create(
            project=self.project, author=self.delegate, body='Reply', parent=parent, depth=1
        )

        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(self.comment_detail_url(parent))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        list_response = self.client.get(self.comments_url())
        by_id = {row['id']: row for row in list_response.data}
        self.assertIsNone(by_id[parent.pk]['body'])
        self.assertIsNone(by_id[parent.pk]['author'])
        self.assertEqual(by_id[reply.pk]['body'], 'Reply')
        self.assertEqual(by_id[reply.pk]['parent'], parent.pk)


class CommentModerationTests(DiscussionsTestCase):
    def test_manager_can_delete_others_comment_as_moderator(self):
        comment = Comment.objects.create(project=self.project, author=self.delegate, body='Original')
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(self.comment_detail_url(comment))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        comment.refresh_from_db()
        self.assertTrue(comment.removed_by_moderator)

        list_response = self.client.get(self.comments_url())
        by_id = {row['id']: row for row in list_response.data}
        self.assertEqual(by_id[comment.pk]['body'], '[Comment removed by moderator]')
        self.assertIsNone(by_id[comment.pk]['author'])

    def test_manager_deleting_own_comment_is_not_moderator_removal(self):
        comment = Comment.objects.create(project=self.project, author=self.manager, body='Original')
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(self.comment_detail_url(comment))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        comment.refresh_from_db()
        self.assertFalse(comment.removed_by_moderator)

    def test_delegate_cannot_delete_others_comment(self):
        comment = Comment.objects.create(project=self.project, author=self.stakeholder, body='Original')
        self.client.force_authenticate(user=self.delegate)
        response = self.client.delete(self.comment_detail_url(comment))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_cannot_delete_comment(self):
        comment = Comment.objects.create(project=self.project, author=self.manager, body='Original')
        self.client.force_authenticate(user=self.stranger)
        response = self.client.delete(self.comment_detail_url(comment))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comments_disabled_blocks_new_top_level_comments(self):
        self.project.comments_enabled = False
        self.project.save(update_fields=['comments_enabled'])

        for user in (self.manager, self.delegate, self.stakeholder):
            self.client.force_authenticate(user=user)
            response = self.client.post(self.comments_url(), {'body': 'Hello'})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_comments_disabled_blocks_replies_too(self):
        root = Comment.objects.create(project=self.project, author=self.manager, body='Root')
        self.project.comments_enabled = False
        self.project.save(update_fields=['comments_enabled'])

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.comments_url(), {'body': 'Reply', 'parent': root.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_comments_disabled_still_allows_reading_and_voting(self):
        comment = Comment.objects.create(project=self.project, author=self.manager, body='Root')
        self.project.comments_enabled = False
        self.project.save(update_fields=['comments_enabled'])

        self.client.force_authenticate(user=self.stakeholder)
        read_response = self.client.get(self.comments_url())
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)

        vote_response = self.client.post(self.vote_url(comment), {'value': 1})
        self.assertEqual(vote_response.status_code, status.HTTP_200_OK)


class CommentVoteTests(DiscussionsTestCase):
    def setUp(self):
        super().setUp()
        self.comment = Comment.objects.create(project=self.project, author=self.manager, body='Vote me')

    def test_user_can_upvote_and_downvote_comment(self):
        self.client.force_authenticate(user=self.delegate)
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['up_count'], 1)
        self.assertEqual(response.data['my_vote'], 1)

    def test_switching_vote_direction_replaces_not_duplicates(self):
        self.client.force_authenticate(user=self.delegate)
        self.client.post(self.vote_url(self.comment), {'value': 1})
        response = self.client.post(self.vote_url(self.comment), {'value': -1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['up_count'], 0)
        self.assertEqual(response.data['down_count'], 1)
        self.assertEqual(
            CommentVote.objects.filter(comment=self.comment, author=self.delegate).count(), 1
        )

    def test_voting_same_direction_twice_removes_vote(self):
        self.client.force_authenticate(user=self.delegate)
        self.client.post(self.vote_url(self.comment), {'value': 1})
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['up_count'], 0)
        self.assertEqual(response.data['my_vote'], None)
        self.assertFalse(CommentVote.objects.filter(comment=self.comment, author=self.delegate).exists())

    def test_vote_uniqueness_db_constraint(self):
        CommentVote.objects.create(comment=self.comment, author=self.delegate, value=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CommentVote.objects.create(comment=self.comment, author=self.delegate, value=-1)

    def test_stakeholder_can_vote(self):
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_vote(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CommentDeleteTreeTests(DiscussionsTestCase):
    def make_tree(self):
        root = Comment.objects.create(project=self.project, author=self.delegate, body='Root')
        child = Comment.objects.create(
            project=self.project, author=self.stakeholder, body='Child', parent=root, depth=1
        )
        grandchild = Comment.objects.create(
            project=self.project, author=self.manager, body='Grandchild', parent=child, depth=2
        )
        unrelated = Comment.objects.create(project=self.project, author=self.manager, body='Unrelated')
        return root, child, grandchild, unrelated

    def test_manager_can_delete_comment_tree(self):
        root, child, grandchild, unrelated = self.make_tree()
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.delete_tree_url(root))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for comment in (root, child, grandchild):
            comment.refresh_from_db()
            self.assertIsNotNone(comment.deleted_at)
            self.assertTrue(comment.removed_by_moderator)
        unrelated.refresh_from_db()
        self.assertIsNone(unrelated.deleted_at)

    def test_delete_tree_leaves_already_deleted_descendants_untouched(self):
        root, child, grandchild, _ = self.make_tree()
        self.client.force_authenticate(user=self.manager)
        original_delete = timezone.now()
        Comment.objects.filter(pk=grandchild.pk).update(
            deleted_at=original_delete, removed_by_moderator=False
        )

        response = self.client.post(self.delete_tree_url(root))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        grandchild.refresh_from_db()
        self.assertEqual(grandchild.deleted_at, original_delete)
        self.assertFalse(grandchild.removed_by_moderator)

    def test_author_who_is_not_manager_cannot_delete_tree(self):
        root, *_ = self.make_tree()
        self.client.force_authenticate(user=self.delegate)
        response = self.client.post(self.delete_tree_url(root))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        root.refresh_from_db()
        self.assertIsNone(root.deleted_at)

    def test_stakeholder_cannot_delete_tree(self):
        root, *_ = self.make_tree()
        self.client.force_authenticate(user=self.stakeholder)
        response = self.client.post(self.delete_tree_url(root))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_cannot_delete_tree(self):
        root, *_ = self.make_tree()
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(self.delete_tree_url(root))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_leaf_comment_tree_only_affects_that_comment(self):
        root, child, grandchild, unrelated = self.make_tree()
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.delete_tree_url(grandchild))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        grandchild.refresh_from_db()
        root.refresh_from_db()
        child.refresh_from_db()
        self.assertIsNotNone(grandchild.deleted_at)
        self.assertIsNone(root.deleted_at)
        self.assertIsNone(child.deleted_at)


class QueryEfficiencyTests(DiscussionsTestCase):
    def test_comment_list_query_count_does_not_scale_with_comment_count(self):
        self.client.force_authenticate(user=self.manager)

        first = Comment.objects.create(project=self.project, author=self.manager, body='First')
        CommentVote.objects.create(comment=first, author=self.delegate, value=1)
        CommentVote.objects.create(comment=first, author=self.stakeholder, value=-1)

        with CaptureQueriesContext(connection) as small:
            self.client.get(self.comments_url())
        baseline = len(small.captured_queries)

        for i in range(15):
            comment = Comment.objects.create(project=self.project, author=self.manager, body=f'Extra {i}')
            CommentVote.objects.create(comment=comment, author=self.delegate, value=1)

        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.comments_url())
        self.assertEqual(len(large.captured_queries), baseline)

        by_id = {row['id']: row for row in response.data}
        self.assertEqual(by_id[first.pk]['up_count'], 1)
        self.assertEqual(by_id[first.pk]['down_count'], 1)
