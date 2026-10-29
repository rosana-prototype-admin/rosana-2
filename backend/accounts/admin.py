from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            'Rosana profile',
            {
                'fields': (
                    'secondary_email',
                    'company',
                    'subscription_type',
                )
            },
        ),
    )
    list_display = (
        'username',
        'email',
        'company',
        'subscription_type',
        'is_staff',
    )
    list_filter = DjangoUserAdmin.list_filter + ('subscription_type',)
