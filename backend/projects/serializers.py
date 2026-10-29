from django.db.models import Q
from rest_framework import serializers

from accounts.models import User
from geo.models import Jcode
from geo.serializers import JcodeSerializer
from focusareas.serializers import InterventionTypeSerializer
from groups.models import Group, Membership

from .models import CASUALTY_TABLE_SIZE, Opportunity, Project, Site, Strategy


class OpportunitySerializer(serializers.ModelSerializer):
    lead_agency_name = serializers.CharField(source='lead_agency.name', read_only=True)
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            'id',
            'title',
            'comment',
            'status',
            'lead_agency',
            'lead_agency_name',
            'assoc_agencies',
            'manager',
            'manager_name',
            'delegates',
            'stakeholders',
            'focus_area',
            'specific_focus_area',
            'created_at',
            'modified_at',
        ]
        # manager is writable here only so perform_create can accept it when
        # the Opportunity is first made -- afterwards it's only reassignable
        # via OpportunityViewSet.member_detail (manager-only gated), same as
        # delegates/stakeholders, which stay fully read-only in this serializer.
        read_only_fields = ['id', 'delegates', 'stakeholders', 'created_at', 'modified_at']

    def get_manager_name(self, obj):
        full_name = f'{obj.manager.first_name} {obj.manager.last_name}'.strip()
        return full_name or obj.manager.username

    def validate(self, attrs):
        if self.instance is not None:
            for field in ('focus_area', 'specific_focus_area'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: 'This field cannot be changed after creation.'})
            # manager is writable in Meta.fields only so perform_create can
            # accept it when the Opportunity is first made; reassigning it
            # afterwards must go through OpportunityViewSet.member_detail
            # (manager-only gated, and only promotes an existing delegate),
            # not a plain PATCH here.
            if 'manager' in attrs and attrs['manager'] != self.instance.manager:
                raise serializers.ValidationError(
                    {'manager': 'The manager can only be reassigned via the members endpoint.'}
                )

        lead_agency = attrs.get('lead_agency', getattr(self.instance, 'lead_agency', None))
        manager = attrs.get('manager', getattr(self.instance, 'manager', None))
        if lead_agency and manager:
            is_lead_agency_admin = lead_agency.admin_id == manager.pk
            is_lead_agency_member = Membership.objects.filter(group=lead_agency, user=manager).exists()
            if not (is_lead_agency_admin or is_lead_agency_member):
                raise serializers.ValidationError(
                    {'manager': 'The manager must be the admin or a member of the lead agency.'}
                )
        return attrs


class OpportunityMemberSerializer(serializers.Serializer):
    """A flattened, read-only view of one Opportunity member (manager, delegate, or stakeholder)."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=['manager', 'delegate', 'stakeholder'])


class InviteMemberSerializer(serializers.Serializer):
    """Adds an existing user to an Opportunity as a delegate or stakeholder."""

    identifier = serializers.CharField(
        write_only=True, help_text='The username or email of an existing user.'
    )
    role = serializers.ChoiceField(choices=['delegate', 'stakeholder'], write_only=True)

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
        if user.pk == opportunity.manager_id:
            raise serializers.ValidationError('This user already manages the opportunity.')
        if opportunity.delegates.filter(pk=user.pk).exists() or opportunity.stakeholders.filter(pk=user.pk).exists():
            raise serializers.ValidationError('This user is already a member of the opportunity.')
        attrs['user'] = user
        return attrs

    def save(self):
        opportunity = self.context['opportunity']
        user = self.validated_data['user']
        if self.validated_data['role'] == 'delegate':
            opportunity.delegates.add(user)
        else:
            opportunity.stakeholders.add(user)
        return user


class InviteGroupSerializer(serializers.Serializer):
    """
    Adds every effective (transitive) member of a Group to an Opportunity as
    stakeholders (read-only viewers) in one action -- unlike InviteMemberSerializer,
    there's no role choice, since "invite this group" specifically means "as viewers".
    Anyone already the manager, a delegate, or a stakeholder is left alone
    rather than being downgraded or duplicated.
    """

    group_id = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), write_only=True)

    def validate_group_id(self, group):
        opportunity = self.context['opportunity']
        existing_ids = {opportunity.manager_id}
        existing_ids.update(opportunity.delegates.values_list('pk', flat=True))
        existing_ids.update(opportunity.stakeholders.values_list('pk', flat=True))
        new_members = [user for user in group.effective_members() if user.pk not in existing_ids]
        if not new_members:
            raise serializers.ValidationError(
                'Every member of this group is already part of the opportunity, or the group has no members.'
            )
        self._new_members = new_members
        return group

    def save(self):
        opportunity = self.context['opportunity']
        opportunity.stakeholders.add(*self._new_members)
        return self._new_members


class ChangeMemberRoleSerializer(serializers.Serializer):
    # 'manager' is only valid when the target user is already a delegate --
    # see OpportunityViewSet.member_detail, which is the sole caller that
    # ever needs to reassign the manager.
    role = serializers.ChoiceField(choices=['manager', 'delegate', 'stakeholder'])


class ProjectSerializer(serializers.ModelSerializer):
    opportunity = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'opportunity', 'title', 'comment', 'status', 'comments_enabled', 'created_at', 'modified_at']
        # comments_enabled is read-only here -- only ProjectViewSet.comments_enabled
        # (manager-only gated) may write it, same convention Opportunity used before this moved.
        read_only_fields = ['id', 'opportunity', 'comments_enabled', 'created_at', 'modified_at']


class SiteSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    jcode = JcodeSerializer(read_only=True)
    jcode_id = serializers.PrimaryKeyRelatedField(
        source='jcode', queryset=Jcode.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Site
        fields = [
            'id',
            'project',
            'jcode',
            'jcode_id',
            'title',
            'comment',
            'site_type',
            'road_class',
            'segment_length',
            'segment_length_unit',
            'gps_x',
            'gps_y',
            'gps_z',
            'aadt',
            'tev',
            'casualty_data_type',
            'casualty_obs',
            'casualty_est',
            'casualty_time_years',
            'casualty_time_months',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'project', 'created_at', 'modified_at']

    def _validate_casualty_array(self, value):
        if not isinstance(value, list) or len(value) != CASUALTY_TABLE_SIZE:
            raise serializers.ValidationError(
                f'Must be a list of {CASUALTY_TABLE_SIZE} integers in CMF table order.'
            )
        if not all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in value):
            raise serializers.ValidationError('All values must be non-negative integers.')
        return value

    def validate_casualty_obs(self, value):
        return self._validate_casualty_array(value)

    def validate_casualty_est(self, value):
        return self._validate_casualty_array(value)

    def validate_casualty_time_years(self, value):
        if value < 0 or value > 25:
            raise serializers.ValidationError('Years must be between 0 and 25.')
        return value

    def validate_casualty_time_months(self, value):
        if value < 0 or value > 11:
            raise serializers.ValidationError('Months must be between 0 and 11.')
        return value

    def validate(self, attrs):
        if 'jcode' in attrs and attrs['jcode'] is not None:
            project = self.instance.project if self.instance is not None else self.context.get('project')
            opportunity = project.get_opportunity() if project is not None else None
            if opportunity is None or not opportunity.lead_agency.jcodes.filter(pk=attrs['jcode'].pk).exists():
                raise serializers.ValidationError(
                    {'jcode_id': "This Jcode is not available through the Opportunity's Lead Agency."}
                )
        return attrs


class StrategySerializer(serializers.ModelSerializer):
    site = serializers.PrimaryKeyRelatedField(read_only=True)
    intervention_type = InterventionTypeSerializer(read_only=True)

    class Meta:
        model = Strategy
        fields = ['id', 'site', 'intervention_type', 'selected', 'details', 'created_at', 'modified_at']
        # intervention_type is fixed at auto-provisioning time (see
        # Site.sync_strategies) -- only `selected` (the checkbox) and
        # `details` (placeholder JSON, fields TBD) are ever written by users.
        read_only_fields = ['id', 'site', 'intervention_type', 'created_at', 'modified_at']

    def validate_details(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('details must be a JSON object.')
        return value
