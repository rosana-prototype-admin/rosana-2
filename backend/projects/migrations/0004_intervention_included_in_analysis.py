from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_rename_courseofaction_to_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='included_in_analysis',
            field=models.BooleanField(default=True),
        ),
    ]
