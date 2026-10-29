from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Renames the CourseOfAction model (and its FK on Intervention) to
    Strategy. Hand-written using RenameModel/RenameField, same reasoning as
    0002_rename_project_to_opportunity.py: these compile to safe
    `ALTER TABLE ... RENAME` statements that preserve existing rows.
    """

    dependencies = [
        ('projects', '0002_rename_project_to_opportunity'),
        # This migration previously also depended on ('analysis', '0001_initial')
        # to avoid a cross-app FK-target-resolution ordering hazard (the
        # analysis app's Projection model targeted 'projects.courseofaction'
        # by name). The analysis app -- and Projection with it -- has since
        # been removed entirely, so that dependency no longer resolves to
        # anything and has been dropped.
    ]

    operations = [
        migrations.RenameModel(
            old_name='CourseOfAction',
            new_name='Strategy',
        ),
        migrations.RenameField(
            model_name='intervention',
            old_name='course_of_action',
            new_name='strategy',
        ),
        migrations.AlterField(
            model_name='strategy',
            name='opportunity',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='strategies',
                to='projects.opportunity',
            ),
        ),
    ]
