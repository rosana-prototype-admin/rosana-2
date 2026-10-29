from rest_framework import serializers

from .models import CountryCode, Jcode


class CountryCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryCode
        fields = ['alpha_2', 'alpha_3', 'name_short', 'name_long']


class JcodeSerializer(serializers.ModelSerializer):
    country_code = CountryCodeSerializer(read_only=True)

    class Meta:
        model = Jcode
        fields = [
            'id',
            'country_code',
            'state',
            'county',
            'place_name_short',
            'place_name_long',
            'census_place_name',
        ]
