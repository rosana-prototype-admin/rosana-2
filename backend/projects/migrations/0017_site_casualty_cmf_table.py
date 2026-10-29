from django.db import migrations, models
from django.core.validators import MinValueValidator, MaxValueValidator
import django.contrib.postgres.fields

import projects.models


def expand_legacy_casualty_arrays(apps, schema_editor):
    Site = apps.get_model('projects', 'Site')

    for site in Site.objects.all().iterator():
        def expand(values):
            legacy_values = list(values or [])[:25]
            if len(legacy_values) == 4:
                # The former fields were Fatal, Serious, Minor, and Property
                # damage only; keep that last value in the matching new
                # column and leave Possible injuries at the initial value.
                legacy_values = legacy_values[:3] + [1, legacy_values[3]]
            # Preserve legacy values in the first cells where possible. A
            # count of zero cannot be represented by the new positive-value
            # table, so legacy empty cells become the neutral initial value.
            expanded = [value if value > 0 else 1 for value in legacy_values]
            return expanded + [1] * (25 - len(expanded))

        site.casualty_obs = expand(site.casualty_obs)
        site.casualty_est = expand(site.casualty_est)
        site.save(update_fields=['casualty_obs', 'casualty_est'])


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0016_site_single_jcode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='casualty_obs',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.IntegerField(validators=[MinValueValidator(1)]),
                blank=True,
                default=projects.models.default_casualty_array,
                size=25,
            ),
        ),
        migrations.AlterField(
            model_name='site',
            name='casualty_est',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.IntegerField(validators=[MinValueValidator(1)]),
                blank=True,
                default=projects.models.default_casualty_array,
                size=25,
            ),
        ),
        migrations.AddField(
            model_name='site',
            name='casualty_time_years',
            field=models.IntegerField(
                default=1,
                validators=[MinValueValidator(1), MaxValueValidator(25)],
            ),
        ),
        migrations.AddField(
            model_name='site',
            name='casualty_time_months',
            field=models.IntegerField(
                default=1,
                validators=[MinValueValidator(1), MaxValueValidator(11)],
            ),
        ),
        migrations.RunPython(expand_legacy_casualty_arrays, migrations.RunPython.noop),
    ]
