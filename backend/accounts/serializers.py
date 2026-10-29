from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'company',
            'secondary_email',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'secondary_email',
            'first_name',
            'last_name',
            'company',
            'subscription_type',
            'language',
            'currency',
            'length_unit',
            'distance_unit',
            'speed_unit',
            'area_small_unit',
            'area_large_unit',
            'volume_unit',
        ]
        read_only_fields = ['id', 'username', 'subscription_type']


class UserSearchResultSerializer(serializers.ModelSerializer):
    """Minimal, non-sensitive fields for directory search results."""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
