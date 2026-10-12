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
        # analysis.0001_initial's Projection.course_of_action FK targets
        # 'projects.courseofaction' by name. Without this explicit edge, the
        # migration planner is free to schedule this rename before that
        # CreateModel runs (it only declares a dependency on
        # projects.0001_initial), which breaks the FK's target resolution
        # during replay even though final state is consistent.
        ('analysis', '0001_initial'),
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
