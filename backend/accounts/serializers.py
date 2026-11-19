from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from groups.models import Group

from .models import AuditEvent, Contract, Plan, SubscriptionSeat, User, UserSubscription
from .staff import validate_staff_account_change


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
        read_only_fields = ['id', 'username', 'email', 'is_staff', 'subscription_type']

    def validate_secondary_email(self, value):
        if value and self.instance and value.casefold() == self.instance.email.casefold():
            raise serializers.ValidationError('Secondary email must be different from the primary email.')
        return value


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
            'secondary_email',
            'first_name',
            'last_name',
            'company',
            'email_verified',
            'is_active',
            'is_staff',
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
        try:
            if instance:
                validate_staff_account_change(
                    instance,
                    is_active=attrs.get('is_active'),
                    is_staff=attrs.get('is_staff'),
                )
        except ValidationError as exc:
            raise serializers.ValidationError({'is_active': exc.messages}) from exc
        return attrs


class AdminSubscriptionSerializer(serializers.ModelSerializer):
    # Older subscription records and older frontend bundles may represent
    # optional text fields as JSON null. Normalize those values rather than
    # rejecting an otherwise valid subscription update.
    external_reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    plan_id = serializers.PrimaryKeyRelatedField(
        source='plan', queryset=Plan.objects.filter(active=True),
        required=False, allow_null=True,
    )

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan_id', 'plan_code', 'acquisition_type', 'status', 'starts_at', 'ends_at',
            'seat_limit', 'external_reference', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_seat_limit(self, value):
        if self.instance and value < self.instance.seats.filter(released_at__isnull=True).count():
            raise serializers.ValidationError('Seat limit cannot be lower than the number of assigned seats.')
        return value

    def validate(self, attrs):
        plan = attrs.get('plan')
        if plan is not None:
            attrs['plan_code'] = plan.code
        if attrs.get('external_reference') is None:
            attrs['external_reference'] = ''
        if attrs.get('notes') is None:
            attrs['notes'] = ''
        return attrs


class OrganizationSubscriptionSerializer(serializers.ModelSerializer):
    """Safe organization-facing subscription fields.

    Payment credentials, negotiated pricing, and internal references are
    deliberately excluded until a billing provider and contract workflow are
    selected.
    """
    plan_id = serializers.PrimaryKeyRelatedField(
        source='plan', queryset=Plan.objects.filter(active=True),
        required=False, allow_null=True,
    )
    plan_name = serializers.CharField(source='plan.name', read_only=True, allow_null=True)

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan_id', 'plan_code', 'plan_name', 'acquisition_type', 'status',
            'starts_at', 'ends_at', 'seat_limit', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'plan_code', 'plan_name', 'acquisition_type', 'created_at', 'updated_at',
        ]

    def validate_seat_limit(self, value):
        if self.instance and value < self.instance.seats.filter(released_at__isnull=True).count():
            raise serializers.ValidationError('Seat limit cannot be lower than assigned seats.')
        return value

    def validate(self, attrs):
        plan = attrs.get('plan')
        if plan is not None:
            attrs['plan_code'] = plan.code
        return attrs


class AdminContractSerializer(serializers.ModelSerializer):
    subscription_id = serializers.PrimaryKeyRelatedField(
        source='subscription', queryset=UserSubscription.objects.all(),
        required=False, allow_null=True,
    )

    class Meta:
        model = Contract
        fields = [
            'id', 'subscription_id', 'title', 'status', 'starts_at', 'ends_at',
            'external_reference', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdminGroupSerializer(serializers.ModelSerializer):
    admin = UserSearchResultSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'parent', 'admin', 'members', 'member_count', 'subscription']

    def get_members(self, obj):
        return UserSearchResultSerializer(obj.effective_members(), many=True).data

    def get_member_count(self, obj):
        return obj.effective_members().count()

    def get_subscription(self, obj):
        subscription = obj.subscriptions.order_by('-starts_at', '-created_at').first()
        return AdminSubscriptionSerializer(subscription).data if subscription else None


class AdminSubscriptionSeatSerializer(serializers.ModelSerializer):
    user = UserSearchResultSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', queryset=User.objects.all(), write_only=True)

    class Meta:
        model = SubscriptionSeat
        fields = ['id', 'user', 'user_id', 'seat_type', 'assigned_at', 'released_at']
        read_only_fields = ['id', 'assigned_at', 'released_at']

    def validate_user(self, user):
        subscription = self.context['subscription']
        if subscription is None:
            raise serializers.ValidationError('Create a subscription before assigning seats.')
        if user not in subscription.group.effective_members():
            raise serializers.ValidationError('The user must belong to this company group before receiving a seat.')
        if subscription.seats.filter(released_at__isnull=True).count() >= subscription.seat_limit:
            raise serializers.ValidationError('This subscription has no available seats.')
        return user


class AdminAuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True, allow_null=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)

    class Meta:
        model = AuditEvent
        fields = [
            'id', 'created_at', 'action', 'entity_type', 'entity_id',
            'actor_username', 'group_name', 'before', 'after',
        ]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value, self.context.get('user'))
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, validators=[validate_password], trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Your current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'The new passwords do not match.'})
        if attrs['new_password'] == attrs['current_password']:
            raise serializers.ValidationError({'new_password': 'The new password must be different from the current password.'})
        return attrs


class DeactivateAccountSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_deactivation = serializers.BooleanField(write_only=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Your current password is incorrect.')
        return value

    def validate_confirm_deactivation(self, value):
        if not value:
            raise serializers.ValidationError('You must confirm that you want to deactivate your account.')
        return value
