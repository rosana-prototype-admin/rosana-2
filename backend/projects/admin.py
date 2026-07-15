from django.contrib import admin

from .models import CourseOfAction, Intervention, Project


class InterventionInline(admin.TabularInline):
    model = Intervention
    extra = 0


class CourseOfActionInline(admin.TabularInline):
    model = CourseOfAction
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'focus_area', 'owner', 'created_at', 'modified_at')
    list_filter = ('focus_area',)
    search_fields = ('name', 'description')
    filter_horizontal = ('editors', 'guests')
    inlines = [CourseOfActionInline]


@admin.register(CourseOfAction)
class CourseOfActionAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_at', 'modified_at')
    list_filter = ('project',)
    search_fields = ('name', 'description')
    inlines = [InterventionInline]


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'course_of_action', 'intervention_type')
    list_filter = ('intervention_type',)
