from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Contract, SubscriptionSeat, User, UserSubscription
from .staff import validate_staff_account_change


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            'Rosana profile',
            {
                'fields': (
                    'secondary_email',
                    'email_verified',
                    'company',
                    'subscription_type',
                )
            },
        ),
    )
    list_display = (
        'username',
        'email',
        'email_verified',
        'company',
        'subscription_type',
        'is_staff',
    )
    list_filter = DjangoUserAdmin.list_filter + ('subscription_type',)

    def save_model(self, request, obj, form, change):
        if change:
            try:
                previous = User.objects.get(pk=obj.pk)
                validate_staff_account_change(
                    previous,
                    is_active=obj.is_active,
                    is_staff=obj.is_staff,
                )
            except User.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('group', 'plan_code', 'status', 'seat_limit', 'starts_at', 'ends_at')
    list_filter = ('plan_code', 'status')
    search_fields = ('group__name', 'external_reference')


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'status', 'starts_at', 'ends_at')
    list_filter = ('status',)
    search_fields = ('title', 'group__name', 'external_reference')


@admin.register(SubscriptionSeat)
class SubscriptionSeatAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'user', 'assigned_at', 'released_at')
    list_filter = ('released_at',)
    search_fields = ('subscription__group__name', 'user__username', 'user__email')
