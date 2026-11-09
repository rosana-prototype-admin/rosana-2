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
        user.email_verified = False
        user.is_active = False
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'is_staff',
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
        read_only_fields = ['id', 'username', 'is_staff', 'subscription_type']


class UserSearchResultSerializer(serializers.ModelSerializer):
    """Minimal, non-sensitive fields for directory search results."""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'company',
            'email_verified',
            'is_active',
            'is_staff',
            'subscription_type',
            'date_joined',
            'last_login',
        ]
        read_only_fields = ['id', 'username', 'email', 'is_staff', 'date_joined', 'last_login']

    def validate(self, attrs):
        instance = self.instance
        request = self.context.get('request')
        if instance and request and instance.pk == request.user.pk and attrs.get('is_active') is False:
            raise serializers.ValidationError({'is_active': 'You cannot deactivate your own account.'})
        if attrs.get('is_active') is True and attrs.get('email_verified', instance.email_verified if instance else False) is False:
            raise serializers.ValidationError({'email_verified': 'An active account must have a verified email.'})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value, self.context.get('user'))
        return value
