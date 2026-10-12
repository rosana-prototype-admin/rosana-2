from django.contrib import admin

from .models import Intervention, Opportunity, Organization, Project, Strategy


class InterventionInline(admin.TabularInline):
    model = Intervention
    extra = 0


class StrategyInline(admin.TabularInline):
    model = Strategy
    extra = 0


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 0


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'focus_area', 'owner', 'created_at', 'modified_at')
    list_filter = ('focus_area',)
    search_fields = ('name', 'description')
    filter_horizontal = ('editors', 'guests')
    inlines = [StrategyInline]


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'opportunity', 'created_at', 'modified_at')
    list_filter = ('opportunity',)
    search_fields = ('name', 'description')
    inlines = [InterventionInline, ProjectInline]


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'strategy', 'intervention_type', 'project')
    list_filter = ('intervention_type',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'strategy', 'created_at', 'modified_at')
    list_filter = ('strategy',)
    search_fields = ('name', 'description')
    filter_horizontal = ('organizations',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
