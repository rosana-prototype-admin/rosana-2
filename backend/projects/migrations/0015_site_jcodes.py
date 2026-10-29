from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geo', '0004_jcode_country_code'),
        ('projects', '0014_opportunity_status_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='jcodes',
            field=models.ManyToManyField(blank=True, related_name='sites', to='geo.jcode'),
        ),
    ]
