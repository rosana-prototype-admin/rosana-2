from django.contrib import admin

from .models import Projection


@admin.register(Projection)
class ProjectionAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'status', 'computed_at')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'modified_at')
