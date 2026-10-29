from rest_framework import serializers

from .models import FocusArea, InterventionType


class FocusAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusArea
        fields = ['id', 'name', 'level', 'parent', 'order']


class FocusAreaL1L2Serializer(serializers.ModelSerializer):
    """Level-2 nodes labeled with their level-1 parent, for the first Opportunity-editor dropdown."""

    label = serializers.SerializerMethodField()

    class Meta:
        model = FocusArea
        fields = ['id', 'label', 'order']

    def get_label(self, obj):
        return f'{obj.parent.name} - {obj.name}' if obj.parent_id else obj.name


class InterventionTypeSerializer(serializers.ModelSerializer):
    cmf = serializers.SerializerMethodField()

    class Meta:
        model = InterventionType
        fields = ['id', 'name', 'category', 'description', 'focus_areas', 'is_active', 'cmf']

    def get_cmf(self, obj):
        cmf = getattr(obj, 'cmf', None)
        if cmf is None:
            return None

        cells = {
            (cell.travel_mode, cell.severity): [
                cell.coefficient_a,
                cell.coefficient_b,
                cell.coefficient_c,
            ]
            for cell in cmf.coefficients.all()
        }
        severities = ('K', 'A', 'B', 'C', 'O')
        coefficient_array = [
            [cells.get((travel_mode, severity), [0.0, 0.0, 0.0]) for severity in severities]
            for travel_mode in range(1, 6)
        ]
        metadata = getattr(cmf, 'metadata', None)
        return {
            'id': cmf.pk,
            'code': cmf.code,
            'title': cmf.title,
            'math': metadata.cmf_math if metadata else 'Q',
            'coefficient_array': coefficient_array,
        }
