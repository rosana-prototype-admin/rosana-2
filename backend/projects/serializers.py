from rest_framework import serializers

from analysis.serializers import ProjectionSerializer

from .models import CourseOfAction, Intervention, Project


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'name',
            'description',
            'focus_area',
            'owner',
            'editors',
            'guests',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'modified_at']


class CourseOfActionSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    projection = ProjectionSerializer(read_only=True)

    class Meta:
        model = CourseOfAction
        fields = [
            'id',
            'project',
            'name',
            'description',
            'projection',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'project', 'projection', 'created_at', 'modified_at']


class InterventionSerializer(serializers.ModelSerializer):
    course_of_action = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Intervention
        fields = [
            'id',
            'course_of_action',
            'intervention_type',
            'parameters',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'course_of_action', 'created_at', 'modified_at']

    def validate(self, attrs):
        intervention_type = attrs.get('intervention_type') or getattr(
            self.instance, 'intervention_type', None
        )
        coa = self.context.get('course_of_action') or getattr(
            self.instance, 'course_of_action', None
        )
        if intervention_type and coa:
            applies = intervention_type.focus_areas.filter(
                pk=coa.project.focus_area_id
            ).exists()
            if not applies:
                raise serializers.ValidationError(
                    {
                        'intervention_type': (
                            "This intervention type is not applicable to the "
                            "project's focus area."
                        )
                    }
                )
        return attrs
