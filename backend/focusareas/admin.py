from django.contrib import admin

from .models import FocusArea, InterventionType


@admin.register(FocusArea)
class FocusAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'parent', 'order')
    list_filter = ('level',)
    search_fields = ('name',)
    autocomplete_fields = ('parent',)
    ordering = ('level', 'parent_id', 'order')


@admin.register(InterventionType)
class InterventionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'cmf', 'is_active')
    list_filter = ('is_active', 'category', 'focus_areas')
    search_fields = ('name', 'category', 'description', 'cmf__code', 'cmf__title')
    autocomplete_fields = ('cmf',)
    filter_horizontal = ('focus_areas',)
