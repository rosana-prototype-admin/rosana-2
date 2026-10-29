import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0011_age_applicability_weights'),
        ('focusareas', '0005_seed_real_intervention_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='interventiontype',
            name='cmf',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='intervention_types',
                to='cmfs.cmf',
            ),
        ),
    ]
