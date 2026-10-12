from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Renames the Project model (and its FK on CourseOfAction) to Opportunity.
    Hand-written rather than autodetected: RenameModel/RenameField compile to
    safe `ALTER TABLE ... RENAME` statements that preserve existing rows,
    unlike a naive AddField+RemoveField pair (which is what an unconfirmed
    autodetector run would produce, silently losing every FK relationship).
    """

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Project',
            new_name='Opportunity',
        ),
        migrations.RenameField(
            model_name='courseofaction',
            old_name='project',
            new_name='opportunity',
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='focus_area',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='opportunities',
                to='focusareas.focusarea',
            ),
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='owned_opportunities',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='editors',
            field=models.ManyToManyField(
                blank=True,
                related_name='editable_opportunities',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='guests',
            field=models.ManyToManyField(
                blank=True,
                related_name='guest_opportunities',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
