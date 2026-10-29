from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from accounts.serializers import UserSearchResultSerializer
from groups.models import Group

from .config import CMF_MOD_CODE_OPTIONS, CMF_LOWER_LIMIT, CMF_UPPER_LIMIT
from .models import CMF, CMFCoefficient, CMFMetadata, CMFUserPermission


TRAVEL_MODES = range(1, 6)
SEVERITIES = ('K', 'A', 'B', 'C', 'O')
METADATA_FIELDS = (
    'cmf_group1', 'cmf_group2', 'cmf_group3',
    'descr_en_us', 'descr_en_au', 'descr_en_ca', 'descr_fr_ca', 'descr_es',
    'cmf_math', 'mod_code1', 'mod_code2', 'mod_code3', 'mod_code4', 'mod_code5',
    'age_0004', 'age_0509', 'age_1014', 'age_1519', 'age_2064', 'age_65up',
)
AGE_FIELDS = ('age_0004', 'age_0509', 'age_1014', 'age_1519', 'age_2064', 'age_65up')
LEGACY_MOD_FIELDS = {
    'roadway_feature': 'mod_code1',
    'vehicle': 'mod_code2',
    'manner_of_collision': 'mod_code3',
    'contributing_circumstance': 'mod_code4',
    'intoxication_status': 'mod_code5',
}
AGE_GROUP_FIELDS = {
    '0-4': 'age_0004',
    '5-9': 'age_0509',
    '10-14': 'age_1014',
    '15-19': 'age_1519',
    '20-64': 'age_2064',
    '65+': 'age_65up',
}


class CMFCoefficientSerializer(serializers.ModelSerializer):
    cmf_code = serializers.CharField(source='cmf.code', read_only=True)

    class Meta:
        model = CMFCoefficient
        fields = ['cmf_code', 'travel_mode', 'severity', 'coefficient_a', 'coefficient_b', 'coefficient_c']

    def validate(self, attrs):
        for field in ('coefficient_a', 'coefficient_b', 'coefficient_c'):
            value = attrs.get(field, 0)
            lower_limit = CMF_LOWER_LIMIT if field == 'coefficient_b' else 0
            if value < lower_limit or value > CMF_UPPER_LIMIT:
                raise serializers.ValidationError({
                    field: f'Coefficient values must be between {lower_limit} and {CMF_UPPER_LIMIT}.'
                })
        return attrs


class CMFMetadataSerializer(serializers.ModelSerializer):
    cmf_code = serializers.CharField(source='cmf.code', read_only=True)

    class Meta:
        model = CMFMetadata
        fields = ['cmf_code', *METADATA_FIELDS]


class CMFUserPermissionSerializer(serializers.ModelSerializer):
    cmf_code = serializers.CharField(source='cmf.code', read_only=True)

    class Meta:
        model = CMFUserPermission
        fields = ['cmf_code', *CMFUserPermission.PLAN_FIELDS]


class CMFSerializer(serializers.ModelSerializer):
    code = serializers.SlugField(read_only=True)
    cmf_code = serializers.SlugField(source='code', read_only=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=64)
    author = UserSearchResultSerializer(read_only=True)
    base_cmf = serializers.PrimaryKeyRelatedField(
        queryset=CMF.objects.filter(is_builtin=True),
        required=False,
        allow_null=True,
    )
    permitted_groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
    )
    metadata = CMFMetadataSerializer(required=False)
    coefficients = CMFCoefficientSerializer(many=True, required=False)
    coefficient_array = serializers.SerializerMethodField()
    user_permissions = CMFUserPermissionSerializer(required=False, allow_null=True)

    # Flat metadata names are retained as an API compatibility layer. They
    # are copied into CMFMetadata and are not stored on CMF itself.
    description = serializers.CharField(required=False, allow_blank=True, write_only=True)
    age_groups = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True, write_only=True
    )
    crash_modification_factors = serializers.JSONField(required=False, allow_null=True, write_only=True)
    roadway_feature = serializers.CharField(required=False, allow_blank=True, write_only=True)
    vehicle = serializers.CharField(required=False, allow_blank=True, write_only=True)
    manner_of_collision = serializers.CharField(required=False, allow_blank=True, write_only=True)
    contributing_circumstance = serializers.CharField(required=False, allow_blank=True, write_only=True)
    intoxication_status = serializers.CharField(required=False, allow_blank=True, write_only=True)
    cmf_group1 = serializers.CharField(required=False, allow_blank=True, write_only=True)
    cmf_group2 = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    cmf_group3 = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    descr_en_us = serializers.CharField(required=False, allow_blank=True, write_only=True)
    descr_en_au = serializers.CharField(required=False, allow_blank=True, write_only=True)
    descr_en_ca = serializers.CharField(required=False, allow_blank=True, write_only=True)
    descr_fr_ca = serializers.CharField(required=False, allow_blank=True, write_only=True)
    descr_es = serializers.CharField(required=False, allow_blank=True, write_only=True)
    cmf_math = serializers.ChoiceField(
        choices=CMFMetadata.Math.choices, required=False, write_only=True
    )
    mod_code1 = serializers.CharField(required=False, allow_blank=True, write_only=True)
    mod_code2 = serializers.CharField(required=False, allow_blank=True, write_only=True)
    mod_code3 = serializers.CharField(required=False, allow_blank=True, write_only=True)
    mod_code4 = serializers.CharField(required=False, allow_blank=True, write_only=True)
    mod_code5 = serializers.CharField(required=False, allow_blank=True, write_only=True)
    age_0004 = serializers.FloatField(required=False, min_value=0, max_value=1, write_only=True)
    age_0509 = serializers.FloatField(required=False, min_value=0, max_value=1, write_only=True)
    age_1014 = serializers.FloatField(required=False, min_value=0, max_value=1, write_only=True)
    age_1519 = serializers.FloatField(required=False, min_value=0, max_value=1, write_only=True)
    age_2064 = serializers.FloatField(required=False, min_value=0, max_value=1, write_only=True)
    age_65up = serializers.FloatField(required=False, min_value=0, max_value=1, write_only=True)

    class Meta:
        model = CMF
        fields = [
            'id', 'code', 'cmf_code', 'title', 'is_builtin', 'author', 'base_cmf',
            'permitted_groups', 'permission_scope', 'cmf_source', 'created_at', 'modified_at',
            'metadata', *METADATA_FIELDS, 'description', 'roadway_feature', 'vehicle',
            'manner_of_collision', 'contributing_circumstance', 'intoxication_status',
            'age_groups', 'crash_modification_factors', 'coefficients', 'coefficient_array',
            'user_permissions',
        ]
        read_only_fields = ['id', 'code', 'cmf_code', 'is_builtin', 'author', 'created_at', 'modified_at']

    def get_coefficient_array(self, obj):
        cells = {
            (cell.travel_mode, cell.severity): [
                cell.coefficient_a,
                cell.coefficient_b,
                cell.coefficient_c,
            ]
            for cell in obj.coefficients.all()
        }
        return [
            [cells.get((travel_mode, severity), [0.0, 0.0, 0.0]) for severity in SEVERITIES]
            for travel_mode in TRAVEL_MODES
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        metadata = getattr(instance, 'metadata', None)
        if metadata is None:
            metadata = CMFMetadata.objects.get_or_create(
                cmf=instance, defaults={'cmf_group1': instance.title}
            )[0]
        metadata_data = CMFMetadataSerializer(metadata).data
        data['metadata'] = metadata_data
        for field in METADATA_FIELDS:
            data[field] = getattr(metadata, field)

        data['description'] = metadata.descr_en_us
        data['roadway_feature'] = metadata.mod_code1
        data['vehicle'] = metadata.mod_code2
        data['manner_of_collision'] = metadata.mod_code3
        data['contributing_circumstance'] = metadata.mod_code4
        data['intoxication_status'] = metadata.mod_code5
        data['age_groups'] = [
            age_group for age_group, field in AGE_GROUP_FIELDS.items() if getattr(metadata, field)
        ]
        data['crash_modification_factors'] = self._legacy_values(instance)
        return data

    @staticmethod
    def _metadata_values(attrs):
        values = dict(attrs.get('metadata') or {})
        for field in METADATA_FIELDS:
            if field in attrs:
                values[field] = attrs[field]
        if 'description' in attrs and 'descr_en_us' not in values:
            values['descr_en_us'] = attrs['description']
        for legacy_field, metadata_field in LEGACY_MOD_FIELDS.items():
            if legacy_field in attrs and metadata_field not in values:
                values[metadata_field] = attrs[legacy_field]
        if 'age_groups' in attrs:
            selected = set(attrs['age_groups'])
            for age_group, field in AGE_GROUP_FIELDS.items():
                values[field] = age_group in selected
        return values

    @staticmethod
    def _pop_metadata_values(validated_data):
        values = dict(validated_data.pop('metadata', {}) or {})
        for field in METADATA_FIELDS:
            if field in validated_data:
                values[field] = validated_data.pop(field)
        if 'description' in validated_data:
            description = validated_data.pop('description')
            values.setdefault('descr_en_us', description)
        for legacy_field, metadata_field in LEGACY_MOD_FIELDS.items():
            if legacy_field in validated_data:
                values.setdefault(metadata_field, validated_data.pop(legacy_field))
        if 'age_groups' in validated_data:
            selected = set(validated_data.pop('age_groups'))
            for age_group, field in AGE_GROUP_FIELDS.items():
                values[field] = age_group in selected
        return values

    def create(self, validated_data):
        coefficients = validated_data.pop('coefficients', None)
        legacy_values = validated_data.pop('crash_modification_factors', None)
        permissions = validated_data.pop('user_permissions', serializers.empty)
        metadata_values = self._pop_metadata_values(validated_data)
        title = validated_data.get('title') or metadata_values.get('cmf_group1') or 'Untitled CMF'
        validated_data['title'] = title
        # Custom CMFs are available to all authenticated users; legacy
        # permission fields remain readable for compatibility only.
        validated_data['permission_scope'] = CMF.PermissionScope.GLOBAL
        if coefficients is None and legacy_values is not None:
            coefficients = self._legacy_coefficients(legacy_values)

        with transaction.atomic():
            instance = super().create(validated_data)
            self._save_metadata(instance, metadata_values, custom=True)
            self._replace_coefficients(instance, coefficients, custom=True)
            self._save_permissions(instance, permissions)
        return instance

    def update(self, instance, validated_data):
        coefficients = validated_data.pop('coefficients', serializers.empty)
        legacy_values = validated_data.pop('crash_modification_factors', serializers.empty)
        permissions = validated_data.pop('user_permissions', serializers.empty)
        metadata_values = self._pop_metadata_values(validated_data)
        if 'title' in validated_data and 'cmf_group1' not in metadata_values:
            metadata_values['cmf_group1'] = validated_data['title']
        if coefficients is serializers.empty and legacy_values is not serializers.empty:
            coefficients = self._legacy_coefficients(legacy_values)

        with transaction.atomic():
            if not instance.is_builtin:
                validated_data['permission_scope'] = CMF.PermissionScope.GLOBAL
            instance = super().update(instance, validated_data)
            if metadata_values:
                self._save_metadata(instance, metadata_values, custom=not instance.is_builtin)
            if coefficients is not serializers.empty:
                self._replace_coefficients(instance, coefficients, custom=not instance.is_builtin)
            if permissions is not serializers.empty:
                self._save_permissions(instance, permissions)
        return instance

    @staticmethod
    def _save_metadata(instance, values, custom=False):
        values = dict(values)
        if not values.get('cmf_group1'):
            values['cmf_group1'] = instance.title or 'Untitled CMF'
        if values.get('cmf_group2') in ('', None):
            values['cmf_group2'] = None
            values['cmf_group3'] = None
        elif values.get('cmf_group3') == '':
            values['cmf_group3'] = None
        if custom:
            values['cmf_math'] = CMFMetadata.Math.QUADRATIC
        CMFMetadata.objects.update_or_create(cmf=instance, defaults=values)

    @staticmethod
    def _legacy_coefficients(values):
        values = values or {}
        travel_modes = ['motorVehicleOccupants', 'motorcyclists', 'bicyclists', 'pedestrians', 'otherRoadUsers']
        severities = ['fatalities', 'seriousInjuries', 'minorInjuries', 'possibleInjuries', 'propertyDamage']
        cells = []
        for travel_mode, road_user_type in enumerate(travel_modes, start=1):
            for severity, injury_type in enumerate(severities):
                raw_value = values.get(road_user_type, {}).get(injury_type, 0)
                cells.append({
                    'travel_mode': travel_mode,
                    'severity': SEVERITIES[severity],
                    'coefficient_a': 0.0,
                    'coefficient_b': raw_value,
                    'coefficient_c': 0.0,
                })
        return cells

    @classmethod
    def _replace_coefficients(cls, instance, coefficients, custom=False):
        coefficients = coefficients or cls._legacy_coefficients(None)
        normalized = []
        for coefficient in coefficients:
            item = dict(coefficient)
            if custom:
                item['coefficient_a'] = 0.0
                item['coefficient_c'] = 0.0
            normalized.append(item)
        CMFCoefficient.objects.filter(cmf=instance).delete()
        CMFCoefficient.objects.bulk_create([
            CMFCoefficient(cmf=instance, **coefficient) for coefficient in normalized
        ])

    @staticmethod
    def _save_permissions(instance, permissions):
        if permissions is serializers.empty:
            return
        if permissions is None:
            CMFUserPermission.objects.filter(cmf=instance).delete()
            return
        CMFUserPermission.objects.update_or_create(cmf=instance, defaults=permissions)

    @staticmethod
    def _legacy_values(instance):
        values = {}
        road_user_types = ['motorVehicleOccupants', 'motorcyclists', 'bicyclists', 'pedestrians', 'otherRoadUsers']
        injury_types = ['fatalities', 'seriousInjuries', 'minorInjuries', 'possibleInjuries', 'propertyDamage']
        cells = {(cell.travel_mode, cell.severity): cell.coefficient_b for cell in instance.coefficients.all()}
        for travel_mode, road_user_type in enumerate(road_user_types, start=1):
            values[road_user_type] = {
                injury_type: cells.get((travel_mode, severity), 0.0)
                for injury_type, severity in zip(injury_types, SEVERITIES)
            }
        return values

    def validate(self, attrs):
        metadata = self._metadata_values(attrs)
        current_metadata = getattr(self.instance, 'metadata', None) if self.instance else None
        group1 = metadata.get('cmf_group1') or getattr(current_metadata, 'cmf_group1', None) or attrs.get('title')
        group2 = metadata.get('cmf_group2', getattr(current_metadata, 'cmf_group2', None))
        group3 = metadata.get('cmf_group3', getattr(current_metadata, 'cmf_group3', None))
        errors = {}
        if not group1 or not group1.strip():
            errors['cmf_group1'] = 'CMFGroup1 is required.'
        if group2 and group2 == group1:
            errors['cmf_group2'] = 'CMFGroup2 must differ from CMFGroup1.'
        if not group2:
            metadata['cmf_group3'] = None
        elif group3 and group3 in (group1, group2):
            errors['cmf_group3'] = 'CMFGroup3 must differ from CMFGroup1 and CMFGroup2.'

        for index, field in enumerate(('mod_code1', 'mod_code2', 'mod_code3', 'mod_code4', 'mod_code5'), start=1):
            value = metadata.get(field, getattr(current_metadata, field, None) if current_metadata else None)
            allowed = CMF_MOD_CODE_OPTIONS[f'ModCode{index}']
            if value and value not in allowed:
                errors[field] = 'Select a valid CMF modification code.'

        coefficients = attrs.get('coefficients')
        if coefficients is not None:
            cells = {(item['travel_mode'], item['severity']) for item in coefficients}
            expected = {(travel_mode, severity) for travel_mode in TRAVEL_MODES for severity in SEVERITIES}
            if len(coefficients) != 25 or cells != expected:
                errors['coefficients'] = 'Provide exactly one coefficient cell for each travel mode and severity.'

        legacy_values = attrs.get('crash_modification_factors')
        if legacy_values is not None:
            self._validate_legacy_values(legacy_values, errors)

        permitted_groups = attrs.get('permitted_groups')
        if permitted_groups is not None:
            if permitted_groups:
                request = self.context.get('request')
                user = request.user if request is not None else None
                if user is None or not user.is_authenticated:
                    errors['permitted_groups'] = 'The CMF author must be authenticated.'
                else:
                    eligible_group_ids = set(
                        Group.objects.filter(
                            Q(admin_id=user.pk) | Q(memberships__user_id=user.pk),
                            pk__in=[group.pk for group in permitted_groups],
                        ).distinct().values_list('pk', flat=True)
                    )
                    if any(group.pk not in eligible_group_ids for group in permitted_groups):
                        errors['permitted_groups'] = 'You may only grant access to agencies you belong to.'

        base_cmf = attrs.get('base_cmf', getattr(self.instance, 'base_cmf', None))
        if base_cmf is not None and self.instance is None:
            request = self.context.get('request')
            if request is not None and CMF.objects.filter(author=request.user, base_cmf=base_cmf).exists():
                errors['base_cmf'] = 'You already have an override for this CMF.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    @staticmethod
    def _validate_legacy_values(values, errors):
        if not isinstance(values, dict):
            errors['crash_modification_factors'] = 'crash_modification_factors must be an object.'
            return
        for road_user_type, injury_values in values.items():
            if not isinstance(injury_values, dict):
                errors.setdefault('crash_modification_factors', {})[road_user_type] = 'Each road user type must contain an object.'
                continue
            for injury_type, raw_value in injury_values.items():
                try:
                    numeric_value = Decimal(str(raw_value))
                except (InvalidOperation, ValueError):
                    errors.setdefault('crash_modification_factors', {}).setdefault(road_user_type, {})[injury_type] = 'CMF values must be numeric.'
                    continue
                if not numeric_value.is_finite() or not (CMF_LOWER_LIMIT <= numeric_value <= CMF_UPPER_LIMIT):
                    errors.setdefault('crash_modification_factors', {}).setdefault(road_user_type, {})[injury_type] = f'CMF values must be between {CMF_LOWER_LIMIT} and {CMF_UPPER_LIMIT}.'
