from django.db import migrations


def wipe_comments(apps, schema_editor):
    # Comments are moving from Opportunity to Project scope; per explicit
    # instruction, existing comments are deleted rather than backfilled onto
    # a project. CommentVote rows cascade automatically.
    Comment = apps.get_model('discussions', 'Comment')
    Comment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('discussions', '0002_comment_removed_by_moderator'),
    ]

    operations = [
        migrations.RunPython(wipe_comments, migrations.RunPython.noop),
    ]
