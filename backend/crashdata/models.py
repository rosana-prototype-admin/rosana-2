from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class CrashCasualtyConversionTableQuerySet(models.QuerySet):
    def resolve_for_analysis(
        self,
        year,
        *,
        country_code='US',
        region_code=None,
        version=None,
        dataset_key='crash-to-casualty',
    ):
        """Resolve the most specific table that covers ``year``.

        A regional table is preferred when one exists. The national table is
        the explicit fallback for the same country and analysis year.
        """
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise ValueError('year must be an integer') from exc

        queryset = self.filter(
            dataset_key=dataset_key,
            country_code__alpha_2__iexact=country_code,
            period_start_year__lte=year,
            period_end_year__gte=year,
        ).prefetch_related('rows')
        if version:
            queryset = queryset.filter(version=version)

        normalized_region = (region_code or '').strip().upper()
        if normalized_region:
            regional = queryset.filter(
                geography_level=CrashCasualtyConversionTable.GeographyLevel.REGION,
                region_code__iexact=normalized_region,
            ).order_by('-is_default', '-period_start_year', '-pk').first()
            if regional is not None:
                return regional

        return queryset.filter(
            geography_level=CrashCasualtyConversionTable.GeographyLevel.NATIONAL,
            region_code='',
        ).order_by('-is_default', '-period_start_year', '-pk').first()


class CrashCasualtyConversionTable(models.Model):
    """A versioned set of crash-to-casualty conversion factors."""

    class GeographyLevel(models.TextChoices):
        NATIONAL = 'national', 'National'
        REGION = 'region', 'State / Province'

    dataset_key = models.SlugField(max_length=100, default='crash-to-casualty')
    version = models.SlugField(max_length=100)
    country_code = models.ForeignKey(
        'geo.CountryCode',
        on_delete=models.PROTECT,
        related_name='crash_casualty_conversion_tables',
    )
    geography_level = models.CharField(max_length=10, choices=GeographyLevel.choices)
    # Blank for a national table; an abbreviation/code such as NY for a
    # regional table. This intentionally does not reference Jcode, because a
    # statewide factor set is not associated with a single place/county code.
    region_code = models.CharField(max_length=10, blank=True)
    period_start_year = models.PositiveSmallIntegerField()
    period_end_year = models.PositiveSmallIntegerField()
    source_title = models.CharField(max_length=500)
    source_version = models.CharField(max_length=100, blank=True)
    source_locator = models.CharField(max_length=500, blank=True)
    source_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = CrashCasualtyConversionTableQuerySet.as_manager()

    class Meta:
        ordering = ['-period_end_year', '-period_start_year', '-modified_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(period_start_year__lte=models.F('period_end_year')),
                name='conversion_period_start_before_end',
            ),
            models.CheckConstraint(
                condition=(
                    Q(geography_level='national', region_code='')
                    | Q(geography_level='region') & ~Q(region_code='')
                ),
                name='conversion_region_matches_geography_level',
            ),
            models.UniqueConstraint(
                fields=[
                    'dataset_key',
                    'version',
                    'country_code',
                    'geography_level',
                    'region_code',
                ],
                name='unique_conversion_table_version_scope',
            ),
            models.UniqueConstraint(
                fields=['dataset_key', 'country_code', 'geography_level', 'region_code'],
                condition=Q(is_default=True),
                name='one_default_conversion_table_per_scope',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.region_code:
            self.region_code = self.region_code.strip().upper()
        else:
            self.region_code = ''
        super().save(*args, **kwargs)

    def __str__(self):
        scope = self.country_code_id
        if self.region_code:
            scope = f'{scope}-{self.region_code}'
        return f'{self.dataset_key} ({scope}, {self.version})'


class CrashCasualtyConversionRow(models.Model):
    """Factors for one crash-severity category in a conversion table."""

    class CrashSeverity(models.TextChoices):
        K = 'K', 'Fatal injury / death'
        A = 'A', 'Serious injury'
        B = 'B', 'Minor injury'
        C = 'C', 'Possible injury'
        O = 'O', 'Property damage only'

    table = models.ForeignKey(
        CrashCasualtyConversionTable,
        on_delete=models.CASCADE,
        related_name='rows',
    )
    crash_severity = models.CharField(max_length=1, choices=CrashSeverity.choices)
    deaths_per_crash = models.DecimalField(
        max_digits=12,
        decimal_places=9,
        validators=[MinValueValidator(Decimal('0'))],
    )
    serious_injuries_per_crash = models.DecimalField(
        max_digits=12,
        decimal_places=9,
        validators=[MinValueValidator(Decimal('0'))],
    )
    minor_injuries_per_crash = models.DecimalField(
        max_digits=12,
        decimal_places=9,
        validators=[MinValueValidator(Decimal('0'))],
    )
    possible_injuries_per_crash = models.DecimalField(
        max_digits=12,
        decimal_places=9,
        validators=[MinValueValidator(Decimal('0'))],
    )
    vehicles_involved_per_crash = models.DecimalField(
        max_digits=12,
        decimal_places=9,
        validators=[MinValueValidator(Decimal('0'))],
    )

    class Meta:
        ordering = ['crash_severity']
        constraints = [
            models.UniqueConstraint(
                fields=['table', 'crash_severity'],
                name='unique_conversion_row_per_severity',
            ),
        ]

    def __str__(self):
        return f'{self.table} - {self.crash_severity}'
