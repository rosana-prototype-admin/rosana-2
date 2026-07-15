from rest_framework import serializers

from .models import Projection


class ProjectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projection
        fields = ['id', 'status', 'result_data', 'computed_at', 'modified_at']
        read_only_fields = fields
