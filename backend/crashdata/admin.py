from django.contrib import admin

from .models import CrashCasualtyConversionRow, CrashCasualtyConversionTable


class CrashCasualtyConversionRowInline(admin.TabularInline):
    model = CrashCasualtyConversionRow
    extra = 0


@admin.register(CrashCasualtyConversionTable)
class CrashCasualtyConversionTableAdmin(admin.ModelAdmin):
    list_display = (
        'dataset_key',
        'version',
        'country_code',
        'geography_level',
        'region_code',
        'period_start_year',
        'period_end_year',
        'is_default',
    )
    list_filter = ('dataset_key', 'country_code', 'geography_level', 'is_default')
    search_fields = ('dataset_key', 'version', 'region_code', 'source_title', 'source_version')
    inlines = [CrashCasualtyConversionRowInline]


@admin.register(CrashCasualtyConversionRow)
class CrashCasualtyConversionRowAdmin(admin.ModelAdmin):
    list_display = ('table', 'crash_severity', 'deaths_per_crash', 'vehicles_involved_per_crash')
    list_filter = ('crash_severity',)
    search_fields = ('table__dataset_key', 'table__version')
