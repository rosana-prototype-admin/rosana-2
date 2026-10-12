import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Follows projects.0003: Projection.course_of_action -> Projection.strategy.
    Depends on the projects rename so the Strategy model already exists in
    migration state by the time this field rename resolves its `to=` target.

    The trailing AlterField restates the `to=` reference explicitly: a
    cross-app RenameModel (in projects.0003) doesn't automatically propagate
    into a field redefined here via RenameField, so without this,
    `makemigrations --check` still reports the field as out of date.
    """

    dependencies = [
        ('analysis', '0001_initial'),
        ('projects', '0003_rename_courseofaction_to_strategy'),
    ]

    operations = [
        migrations.RenameField(
            model_name='projection',
            old_name='course_of_action',
            new_name='strategy',
        ),
        migrations.AlterField(
            model_name='projection',
            name='strategy',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='projection',
                to='projects.strategy',
            ),
        ),
    ]
