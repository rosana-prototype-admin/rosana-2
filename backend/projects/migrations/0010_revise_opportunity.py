import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Revises Opportunity from the blank-slate {name, description, focus_area,
    owner/editors/guests} shape into the full field set: title/comment (name/
    description renamed and re-typed), status, lead_agency/assoc_agencies,
    manager/delegates/stakeholders (replacing owner/editors/guests as the
    access-control roles), and specific_focus_area alongside the existing
    focus_area. Runs against an empty Opportunity table (see 0009), so the
    new required lead_agency/manager columns need no default.
    """

    dependencies = [
        ('projects', '0009_wipe_opportunities'),
        ('groups', '0002_group_jcodes'),
        ('focusareas', '0005_seed_real_intervention_types'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name='opportunity',
            old_name='name',
            new_name='title',
        ),
        migrations.RenameField(
            model_name='opportunity',
            old_name='description',
            new_name='comment',
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='title',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='comment',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.RemoveField(
            model_name='opportunity',
            name='owner',
        ),
        migrations.RemoveField(
            model_name='opportunity',
            name='editors',
        ),
        migrations.RemoveField(
            model_name='opportunity',
            name='guests',
        ),
        migrations.AddField(
            model_name='opportunity',
            name='status',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='opportunity',
            name='lead_agency',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='led_opportunities',
                to='groups.group',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='opportunity',
            name='assoc_agencies',
            field=models.ManyToManyField(
                blank=True, related_name='assoc_opportunities', to='groups.group'
            ),
        ),
        migrations.AddField(
            model_name='opportunity',
            name='manager',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='managed_opportunities',
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='opportunity',
            name='delegates',
            field=models.ManyToManyField(
                blank=True, related_name='delegate_opportunities', to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='opportunity',
            name='stakeholders',
            field=models.ManyToManyField(
                blank=True, related_name='stakeholder_opportunities', to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='opportunity',
            name='specific_focus_area',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='focusareas.focusarea',
            ),
        ),
    ]
