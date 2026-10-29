import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geo', '0003_countrycode'),
    ]

    operations = [
        migrations.AddField(
            model_name='jcode',
            name='country_code',
            field=models.ForeignKey(
                default='US',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='jcodes',
                to='geo.countrycode',
            ),
        ),
    ]
