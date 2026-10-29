import django.db.models.deletion
from django.db import migrations, models


def copy_first_site_jcode(apps, schema_editor):
    Site = apps.get_model('projects', 'Site')

    for site in Site.objects.all().iterator():
        jcode = site.jcodes.order_by('id').first()
        if jcode is not None:
            site.jcode_id = jcode.pk
            site.save(update_fields=['jcode'])


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0015_site_jcodes'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='jcode',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sites',
                to='geo.jcode',
            ),
        ),
        migrations.RunPython(copy_first_site_jcode, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='site',
            name='jcodes',
        ),
    ]
