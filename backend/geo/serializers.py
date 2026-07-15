from rest_framework import serializers

from .models import Jcode


class JcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jcode
        fields = [
            'id',
            'state',
            'county',
            'place_name_short',
            'place_name_long',
            'census_place_name',
        ]
