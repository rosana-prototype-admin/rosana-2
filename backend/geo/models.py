from django.db import models


class CountryCode(models.Model):
    """An ISO 3166-1 country/territory code."""

    alpha_2 = models.CharField(max_length=2, primary_key=True)
    alpha_3 = models.CharField(max_length=3, unique=True)
    name_short = models.CharField(max_length=255)
    name_long = models.CharField(max_length=255)

    class Meta:
        ordering = ['name_short']

    def __str__(self):
        return self.name_short


class Jcode(models.Model):
    """A unique identifier for a geographic jurisdiction (state/county/place)."""

    id = models.CharField(max_length=20, primary_key=True)
    # Every Jcode currently comes from Census place-code/population-estimate
    # files, which are exclusively US -- 'US' is a sensible default rather
    # than a required field every import/creation site must fill in.
    country_code = models.ForeignKey(CountryCode, on_delete=models.PROTECT, related_name='jcodes', default='US')
    state = models.CharField(max_length=100)
    county = models.CharField(max_length=100, blank=True)
    place_name_short = models.CharField(max_length=255)
    place_name_long = models.CharField(max_length=255)
    census_place_name = models.CharField(max_length=255, blank=True)

    # Census geography/methodology codes, populated from population estimate
    # files (Census Bureau SUMLEV/STATE/COUNTY/PLACE/COUSUB/CONCIT/
    # PRIMGEO_FLAG/FUNCSTAT). Optional since Jcodes created from place-code
    # files alone won't have them yet.
    sumlev = models.PositiveSmallIntegerField(null=True, blank=True)
    state_fips = models.PositiveSmallIntegerField(null=True, blank=True)
    county_fips = models.PositiveIntegerField(null=True, blank=True)
    place_fips = models.PositiveIntegerField(null=True, blank=True)
    cousub_fips = models.PositiveIntegerField(null=True, blank=True)
    concit_fips = models.PositiveIntegerField(null=True, blank=True)
    primgeo_flag = models.PositiveSmallIntegerField(null=True, blank=True)
    funcstat = models.CharField(max_length=1, blank=True)

    class Meta:
        ordering = ['state', 'county', 'place_name_short']

    def __str__(self):
        return f'{self.place_name_short} ({self.id})'


class PopulationEstimate(models.Model):
    """A single year's population figure for a Jcode.

    One row per (jcode, year, series) rather than a column per year, so a
    new Census vintage (e.g. POPESTIMATE2026) is just new rows next year,
    not a migration.
    """

    class Series(models.TextChoices):
        BASE = 'base', 'Estimates Base'
        ESTIMATE = 'estimate', 'Population Estimate'

    jcode = models.ForeignKey(Jcode, on_delete=models.CASCADE, related_name='population_estimates')
    year = models.PositiveSmallIntegerField()
    series = models.CharField(max_length=10, choices=Series.choices, default=Series.ESTIMATE)
    population = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['jcode', 'year', 'series'], name='unique_jcode_year_series'),
        ]
        ordering = ['jcode', 'year', 'series']

    def __str__(self):
        return f'{self.jcode_id} {self.year} ({self.series}): {self.population}'
