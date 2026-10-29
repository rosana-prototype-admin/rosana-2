from django.contrib import admin

from .models import CountryCode, Jcode, PopulationEstimate


@admin.register(CountryCode)
class CountryCodeAdmin(admin.ModelAdmin):
    list_display = ('alpha_2', 'alpha_3', 'name_short', 'name_long')
    search_fields = ('alpha_2', 'alpha_3', 'name_short', 'name_long')


@admin.register(Jcode)
class JcodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'country_code', 'state', 'county', 'place_name_short')
    list_filter = ('country_code', 'state')
    search_fields = ('id', 'state', 'county', 'place_name_short', 'place_name_long')


@admin.register(PopulationEstimate)
class PopulationEstimateAdmin(admin.ModelAdmin):
    list_display = ('jcode', 'year', 'series', 'population')
    list_filter = ('series', 'year')
    search_fields = ('jcode__id', 'jcode__place_name_short')
