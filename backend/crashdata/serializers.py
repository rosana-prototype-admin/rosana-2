from rest_framework import serializers

from .models import CrashCasualtyConversionRow, CrashCasualtyConversionTable


class CrashCasualtyConversionRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrashCasualtyConversionRow
        fields = [
            'crash_severity',
            'deaths_per_crash',
            'serious_injuries_per_crash',
            'minor_injuries_per_crash',
            'possible_injuries_per_crash',
            'vehicles_involved_per_crash',
        ]
        read_only_fields = fields


class CrashCasualtyConversionTableSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source='country_code_id', read_only=True)
    rows = CrashCasualtyConversionRowSerializer(many=True, read_only=True)

    class Meta:
        model = CrashCasualtyConversionTable
        fields = [
            'id',
            'dataset_key',
            'version',
            'country_code',
            'geography_level',
            'region_code',
            'period_start_year',
            'period_end_year',
            'source_title',
            'source_version',
            'source_locator',
            'source_url',
            'notes',
            'is_default',
            'rows',
        ]
        read_only_fields = fields
