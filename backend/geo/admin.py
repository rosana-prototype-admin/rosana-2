from django.contrib import admin

from .models import Jcode, PopulationEstimate


@admin.register(Jcode)
class JcodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'state', 'county', 'place_name_short')
    list_filter = ('state',)
    search_fields = ('id', 'state', 'county', 'place_name_short', 'place_name_long')


@admin.register(PopulationEstimate)
class PopulationEstimateAdmin(admin.ModelAdmin):
    list_display = ('jcode', 'year', 'series', 'population')
    list_filter = ('series', 'year')
    search_fields = ('jcode__id', 'jcode__place_name_short')
