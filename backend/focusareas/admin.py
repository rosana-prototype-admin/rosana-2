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
    list_display = ('name', 'is_active')
    list_filter = ('is_active', 'focus_areas')
    search_fields = ('name', 'description')
    filter_horizontal = ('focus_areas',)
