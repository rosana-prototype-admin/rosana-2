from django.db.models import Q
from rest_framework import serializers

from accounts.models import User
from analysis.serializers import ProjectionSerializer

from .models import Intervention, Opportunity, Organization, Project, Strategy


class OpportunitySerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Opportunity
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


class StrategySerializer(serializers.ModelSerializer):
    opportunity = serializers.PrimaryKeyRelatedField(read_only=True)
    projection = ProjectionSerializer(read_only=True)

    class Meta:
        model = Strategy
        fields = [
            'id',
            'opportunity',
            'name',
            'description',
            'projection',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'opportunity', 'projection', 'created_at', 'modified_at']


class InterventionSerializer(serializers.ModelSerializer):
    strategy = serializers.PrimaryKeyRelatedField(read_only=True)
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Intervention
        fields = [
            'id',
            'strategy',
            'intervention_type',
            'parameters',
            'included_in_analysis',
            'project',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'strategy', 'created_at', 'modified_at']

    def validate(self, attrs):
        intervention_type = attrs.get('intervention_type') or getattr(
            self.instance, 'intervention_type', None
        )
        strategy = self.context.get('strategy') or getattr(
            self.instance, 'strategy', None
        )
        if intervention_type and strategy:
            applies = intervention_type.focus_areas.filter(
                pk=strategy.opportunity.focus_area_id
            ).exists()
            if not applies:
                raise serializers.ValidationError(
                    {
                        'intervention_type': (
                            "This intervention type is not applicable to the "
                            "opportunity's focus area."
                        )
                    }
                )

        project = attrs.get('project')
        if project and strategy and project.strategy_id != strategy.pk:
            raise serializers.ValidationError(
                {
                    'project': (
                        "This project does not belong to the same Strategy as "
                        "this Intervention."
                    )
                }
            )
        return attrs


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name']


class ProjectSerializer(serializers.ModelSerializer):
    strategy = serializers.PrimaryKeyRelatedField(read_only=True)
    organizations = OrganizationSerializer(many=True, read_only=True)
    organization_ids = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='organizations',
    )
    interventions = InterventionSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'strategy',
            'name',
            'description',
            'organizations',
            'organization_ids',
            'interventions',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'strategy', 'interventions', 'created_at', 'modified_at']


class OpportunityMemberSerializer(serializers.Serializer):
    """A flattened, read-only view of one Opportunity member (owner, editor, or guest)."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=['owner', 'editor', 'guest'])


class InviteMemberSerializer(serializers.Serializer):
    """Adds an existing user to an Opportunity as an editor or guest."""

    identifier = serializers.CharField(
        write_only=True, help_text='The username or email of an existing user.'
    )
    role = serializers.ChoiceField(choices=['editor', 'guest'], write_only=True)

    def validate_identifier(self, value):
        matches = User.objects.filter(Q(username__iexact=value) | Q(email__iexact=value))
        count = matches.count()
        if count == 0:
            raise serializers.ValidationError('No user found with that username or email.')
        if count > 1:
            raise serializers.ValidationError('Multiple users matched; use their exact username.')
        self._user = matches.get()
        return value

    def validate(self, attrs):
        opportunity = self.context['opportunity']
        user = self._user
        if user.pk == opportunity.owner_id:
            raise serializers.ValidationError('This user already owns the opportunity.')
        if opportunity.editors.filter(pk=user.pk).exists() or opportunity.guests.filter(pk=user.pk).exists():
            raise serializers.ValidationError('This user is already a member of the opportunity.')
        attrs['user'] = user
        return attrs

    def save(self):
        opportunity = self.context['opportunity']
        user = self.validated_data['user']
        if self.validated_data['role'] == 'editor':
            opportunity.editors.add(user)
        else:
            opportunity.guests.add(user)
        return user


class ChangeMemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['editor', 'guest'])
