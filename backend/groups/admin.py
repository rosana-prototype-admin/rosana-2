from django.contrib import admin

from .models import Group, Membership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'admin', 'created_at', 'modified_at')
    list_filter = ('parent',)
    search_fields = ('name',)
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'roles')
    list_filter = ('group',)
