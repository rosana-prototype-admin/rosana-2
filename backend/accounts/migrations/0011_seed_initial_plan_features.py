from django.db import migrations


CORE_FEATURES = {
    'view_existing',
    'analyze',
    'manage_billing',
    'manage_users',
    'manage_groups',
    'delete_resources',
}

# The exact commercial tier mapping is still pending. The current catalog
# names indicate that Basic is the lowest non-collaborative tier; this mapping
# is intentionally easy to revise in the admin catalog later.
COLLABORATION_PLANS = {
    'premium',
    'admin',
    'crossroads',
    'borough',
    'ville',
    'shire',
    'provincia',
    'comarca',
    'metro',
    'commonwealth',
    'republic',
}


def seed_initial_plan_features(apps, schema_editor):
    Plan = apps.get_model('accounts', 'Plan')
    PlanFeature = apps.get_model('accounts', 'PlanFeature')

    for plan in Plan.objects.exclude(code='none').filter(active=True):
        feature_codes = set(CORE_FEATURES)
        if plan.code in COLLABORATION_PLANS:
            feature_codes.add('comment')
        for feature_code in feature_codes:
            PlanFeature.objects.get_or_create(
                plan_id=plan.pk,
                feature_code=feature_code,
                defaults={'enabled': True},
            )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0010_entitlement_roles'),
    ]

    operations = [
        migrations.RunPython(seed_initial_plan_features, migrations.RunPython.noop),
    ]
