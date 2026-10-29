from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geo', '0002_jcode_concit_fips_jcode_county_fips_and_more'),
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='jcodes',
            field=models.ManyToManyField(blank=True, related_name='groups', to='geo.jcode'),
        ),
    ]
