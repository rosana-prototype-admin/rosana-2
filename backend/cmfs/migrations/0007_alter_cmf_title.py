from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cmfs', '0006_structured_cmf_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cmf',
            name='title',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
