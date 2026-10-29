from django.contrib import admin

from .models import Opportunity, Project, Site, Strategy


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'focus_area', 'lead_agency', 'manager', 'status', 'created_at', 'modified_at')
    list_filter = ('focus_area', 'lead_agency', 'status')
    search_fields = ('title', 'comment')
    filter_horizontal = ('assoc_agencies', 'delegates', 'stakeholders')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'opportunity', 'status', 'created_at', 'modified_at')
    list_filter = ('status',)
    search_fields = ('title', 'comment')


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'site_type', 'road_class', 'created_at', 'modified_at')
    list_filter = ('site_type',)
    search_fields = ('title', 'comment')


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('id', 'site', 'intervention_type', 'selected', 'created_at', 'modified_at')
    list_filter = ('intervention_type', 'selected')
