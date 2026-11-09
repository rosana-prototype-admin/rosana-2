from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0005_user_email_verified')]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending'), ('active', 'Active'), ('expired', 'Expired'), ('terminated', 'Terminated')], default='draft', max_length=20)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('external_reference', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_code', models.CharField(choices=[('none', 'None'), ('basic', 'Basic'), ('premium', 'Premium'), ('admin', 'Admin'), ('crossroads', 'Crossroads'), ('borough', 'Borough'), ('ville', 'Ville'), ('shire', 'Shire'), ('provincia', 'Provincia'), ('comarca', 'Comarca'), ('metro', 'Metro'), ('commonwealth', 'Commonwealth'), ('republic', 'Republic')], max_length=20)),
                ('status', models.CharField(choices=[('trialing', 'Trialing'), ('active', 'Active'), ('paused', 'Paused'), ('past_due', 'Past due'), ('canceled', 'Canceled'), ('expired', 'Expired')], default='active', max_length=20)),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('external_reference', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='accounts.user')),
            ],
            options={'ordering': ['-starts_at', '-created_at']},
        ),
    ]
