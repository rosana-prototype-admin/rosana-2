from django.db import IntegrityError, transaction
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from focusareas.models import FocusArea
from projects.models import Opportunity

from .models import Comment, CommentVote


class DiscussionsTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='pw')
        self.editor = User.objects.create_user(username='editor', email='editor@example.com', password='pw')
        self.guest = User.objects.create_user(username='guest', email='guest@example.com', password='pw')
        self.stranger = User.objects.create_user(username='stranger', email='stranger@example.com', password='pw')

        focus_area = FocusArea.objects.get(name='Vulnerable Road Users')
        self.opportunity = Opportunity.objects.create(
            name='Test Opportunity', focus_area=focus_area, owner=self.owner
        )
        self.opportunity.editors.add(self.editor)
        self.opportunity.guests.add(self.guest)

    def comments_url(self, opportunity=None):
        return f'/api/opportunities/{(opportunity or self.opportunity).pk}/comments/'

    def comment_detail_url(self, comment):
        return f'/api/comments/{comment.pk}/'

    def vote_url(self, comment):
        return f'/api/comments/{comment.pk}/vote/'


class CommentRoleTests(DiscussionsTestCase):
    def test_owner_can_post_comment(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_editor_can_post_comment(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_guest_can_post_comment(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author']['id'], self.guest.pk)

    def test_stranger_cannot_post_comment(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(self.comments_url(), {'body': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_editor_guest_can_read_comments(self):
        Comment.objects.create(opportunity=self.opportunity, author=self.owner, body='Hi')
        for user in (self.owner, self.editor, self.guest):
            self.client.force_authenticate(user=user)
            response = self.client.get(self.comments_url())
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)

    def test_stranger_cannot_read_comments(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(self.comments_url())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comment_must_be_created_via_nested_route(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post('/api/comments/', {'body': 'Flat create'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CommentThreadingTests(DiscussionsTestCase):
    def test_reply_created_with_correct_parent_and_depth(self):
        root = Comment.objects.create(opportunity=self.opportunity, author=self.owner, body='Root')
        self.client.force_authenticate(user=self.editor)
        response = self.client.post(self.comments_url(), {'body': 'Reply', 'parent': root.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['parent'], root.pk)
        self.assertEqual(response.data['depth'], 1)

    def test_reply_rejected_when_parent_belongs_to_different_opportunity(self):
        other_opportunity = Opportunity.objects.create(
            name='Other', focus_area=self.opportunity.focus_area, owner=self.owner
        )
        other_root = Comment.objects.create(opportunity=other_opportunity, author=self.owner, body='Root')

        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.comments_url(), {'body': 'Reply', 'parent': other_root.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reply_up_to_max_depth_is_accepted_past_is_rejected(self):
        self.client.force_authenticate(user=self.owner)
        comment = Comment.objects.create(opportunity=self.opportunity, author=self.owner, body='Depth 0')
        for expected_depth in range(1, Comment.MAX_DEPTH + 1):
            response = self.client.post(self.comments_url(), {'body': f'Depth {expected_depth}', 'parent': comment.pk})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['depth'], expected_depth)
            comment = Comment.objects.get(pk=response.data['id'])

        response = self.client.post(self.comments_url(), {'body': 'Too deep', 'parent': comment.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CommentEditDeleteTests(DiscussionsTestCase):
    def test_author_can_edit_own_comment(self):
        comment = Comment.objects.create(opportunity=self.opportunity, author=self.editor, body='Original')
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(self.comment_detail_url(comment), {'body': 'Edited'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['body'], 'Edited')

    def test_non_author_cannot_edit_comment(self):
        comment = Comment.objects.create(opportunity=self.opportunity, author=self.editor, body='Original')
        # Owner and editor-of-the-opportunity both pass can_write/can_read but
        # are NOT the comment's author, so they must still be rejected --
        # this is what would catch an accidental fallback to can_write semantics.
        for user in (self.owner, self.guest):
            self.client.force_authenticate(user=user)
            response = self.client.patch(self.comment_detail_url(comment), {'body': 'Hacked'})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_delete_own_comment_soft_deletes(self):
        comment = Comment.objects.create(opportunity=self.opportunity, author=self.guest, body='Original')
        self.client.force_authenticate(user=self.guest)
        response = self.client.delete(self.comment_detail_url(comment))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        comment.refresh_from_db()
        self.assertIsNotNone(comment.deleted_at)
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

    def test_deleting_comment_preserves_replies_and_tombstones_body(self):
        parent = Comment.objects.create(opportunity=self.opportunity, author=self.owner, body='Parent')
        reply = Comment.objects.create(
            opportunity=self.opportunity, author=self.editor, body='Reply', parent=parent, depth=1
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.comment_detail_url(parent))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        list_response = self.client.get(self.comments_url())
        by_id = {row['id']: row for row in list_response.data}
        self.assertIsNone(by_id[parent.pk]['body'])
        self.assertIsNone(by_id[parent.pk]['author'])
        self.assertEqual(by_id[reply.pk]['body'], 'Reply')
        self.assertEqual(by_id[reply.pk]['parent'], parent.pk)


class CommentVoteTests(DiscussionsTestCase):
    def setUp(self):
        super().setUp()
        self.comment = Comment.objects.create(opportunity=self.opportunity, author=self.owner, body='Vote me')

    def test_user_can_upvote_and_downvote_comment(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['up_count'], 1)
        self.assertEqual(response.data['my_vote'], 1)

    def test_switching_vote_direction_replaces_not_duplicates(self):
        self.client.force_authenticate(user=self.editor)
        self.client.post(self.vote_url(self.comment), {'value': 1})
        response = self.client.post(self.vote_url(self.comment), {'value': -1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['up_count'], 0)
        self.assertEqual(response.data['down_count'], 1)
        self.assertEqual(
            CommentVote.objects.filter(comment=self.comment, author=self.editor).count(), 1
        )

    def test_voting_same_direction_twice_removes_vote(self):
        self.client.force_authenticate(user=self.editor)
        self.client.post(self.vote_url(self.comment), {'value': 1})
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['up_count'], 0)
        self.assertEqual(response.data['my_vote'], None)
        self.assertFalse(CommentVote.objects.filter(comment=self.comment, author=self.editor).exists())

    def test_vote_uniqueness_db_constraint(self):
        CommentVote.objects.create(comment=self.comment, author=self.editor, value=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CommentVote.objects.create(comment=self.comment, author=self.editor, value=-1)

    def test_guest_can_vote(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_vote(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(self.vote_url(self.comment), {'value': 1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class QueryEfficiencyTests(DiscussionsTestCase):
    def test_comment_list_query_count_does_not_scale_with_comment_count(self):
        self.client.force_authenticate(user=self.owner)

        first = Comment.objects.create(opportunity=self.opportunity, author=self.owner, body='First')
        CommentVote.objects.create(comment=first, author=self.editor, value=1)
        CommentVote.objects.create(comment=first, author=self.guest, value=-1)

        with CaptureQueriesContext(connection) as small:
            self.client.get(self.comments_url())
        baseline = len(small.captured_queries)

        for i in range(15):
            comment = Comment.objects.create(opportunity=self.opportunity, author=self.owner, body=f'Extra {i}')
            CommentVote.objects.create(comment=comment, author=self.editor, value=1)

        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.comments_url())
        self.assertEqual(len(large.captured_queries), baseline)

        by_id = {row['id']: row for row in response.data}
        self.assertEqual(by_id[first.pk]['up_count'], 1)
        self.assertEqual(by_id[first.pk]['down_count'], 1)
