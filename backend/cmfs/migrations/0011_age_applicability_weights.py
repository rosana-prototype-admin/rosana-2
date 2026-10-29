from django.db import migrations, models


AGE_FIELDS = (
    'age_0004',
    'age_0509',
    'age_1014',
    'age_1519',
    'age_2064',
    'age_65up',
)


BOOL_TO_WEIGHT_SQL = [
    f'ALTER TABLE "cmfs_cmfmetadata" ALTER COLUMN "{field}" TYPE double precision '
    f'USING CASE WHEN "{field}" THEN 1.0 ELSE 0.0 END'
    for field in AGE_FIELDS
]
WEIGHT_TO_BOOL_SQL = [
    f'ALTER TABLE "cmfs_cmfmetadata" ALTER COLUMN "{field}" TYPE boolean '
    f'USING CASE WHEN "{field}" >= 0.5 THEN TRUE ELSE FALSE END'
    for field in AGE_FIELDS
]


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0010_alter_cmfcoefficient_limits'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=BOOL_TO_WEIGHT_SQL,
                    reverse_sql=WEIGHT_TO_BOOL_SQL,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='cmfmetadata',
                    name=field,
                    field=models.FloatField(default=0.0),
                )
                for field in AGE_FIELDS
            ],
        ),
    ]
