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
    class Meta:
        model = InterventionType
        fields = ['id', 'name', 'description', 'focus_areas', 'is_active']
