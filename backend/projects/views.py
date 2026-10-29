from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import User
from geo.serializers import JcodeSerializer

from .cloning import clone_opportunity
from .models import Opportunity, Project, Site, Strategy
from .permissions import (
    OpportunityAccessPermission,
    ProjectAncestorScopedMixin,
    SiteAncestorScopedMixin,
    StrategyAncestorScopedMixin,
    can_invite,
    can_manage_roles,
)
from .serializers import (
    ChangeMemberRoleSerializer,
    InviteGroupSerializer,
    InviteMemberSerializer,
    OpportunityMemberSerializer,
    OpportunitySerializer,
    ProjectSerializer,
    SiteSerializer,
    StrategySerializer,
)


def _opportunity_members(opportunity):
    """Flatten manager + delegates + stakeholders into one role-tagged list."""
    def _entry(user, role):
        return {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': role,
        }

    members = [_entry(opportunity.manager, 'manager')]
    members += [_entry(user, 'delegate') for user in opportunity.delegates.all()]
    members += [_entry(user, 'stakeholder') for user in opportunity.stakeholders.all()]
    return members


class OpportunityViewSet(viewsets.ModelViewSet):
    serializer_class = OpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        return (
            Opportunity.objects.visible_to(self.request.user)
            .select_related('focus_area', 'specific_focus_area', 'lead_agency', 'manager')
            .prefetch_related('assoc_agencies', 'delegates', 'stakeholders')
        )

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        # Cloning only requires read access: it never mutates the source
        # opportunity, only creates a brand-new one the requester can work with.
        opportunity = get_object_or_404(self.get_queryset(), pk=pk)
        cloned = clone_opportunity(opportunity, requester=request.user)
        return Response(OpportunitySerializer(cloned).data, status=201)

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        if request.method == 'POST':
            # Inviting is manager-only (can_invite), which is stricter than the
            # can_write check OpportunityAccessPermission would apply by
            # default, so fetch via the read-scoped queryset and check explicitly.
            opportunity = get_object_or_404(self.get_queryset(), pk=pk)
            if not can_invite(request.user, opportunity):
                raise PermissionDenied('You do not have permission to invite members to this opportunity.')
            serializer = InviteMemberSerializer(data=request.data, context={'opportunity': opportunity})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                OpportunityMemberSerializer(_opportunity_members(opportunity), many=True).data, status=201
            )

        # GET: any read access (manager/delegate/stakeholder) may view the member list.
        opportunity = self.get_object()
        return Response(OpportunityMemberSerializer(_opportunity_members(opportunity), many=True).data)

    @action(detail=True, methods=['post'], url_path='invite-group')
    def invite_group(self, request, pk=None):
        # Manager-only, same gate as the single-user invite above.
        opportunity = get_object_or_404(self.get_queryset(), pk=pk)
        if not can_invite(request.user, opportunity):
            raise PermissionDenied('You do not have permission to invite members to this opportunity.')
        serializer = InviteGroupSerializer(data=request.data, context={'opportunity': opportunity})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            OpportunityMemberSerializer(_opportunity_members(opportunity), many=True).data, status=201
        )

    @action(detail=True, methods=['patch', 'delete'], url_path=r'members/(?P<user_id>\d+)')
    def member_detail(self, request, pk=None, user_id=None):
        opportunity = get_object_or_404(self.get_queryset(), pk=pk)
        if not can_manage_roles(request.user, opportunity):
            raise PermissionDenied("You do not have permission to manage this opportunity's members.")

        is_delegate = opportunity.delegates.filter(pk=user_id).exists()
        is_stakeholder = opportunity.stakeholders.filter(pk=user_id).exists()

        if request.method == 'DELETE':
            if not (is_delegate or is_stakeholder):
                raise NotFound('This user is not a member of the opportunity.')
            member = get_object_or_404(User, pk=user_id)
            opportunity.delegates.remove(member)
            opportunity.stakeholders.remove(member)
            return Response(status=204)

        serializer = ChangeMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data['role']
        member = get_object_or_404(User, pk=user_id)

        if new_role == 'manager':
            # Promoting a delegate to manager demotes the current manager to
            # delegate -- there is always exactly one manager.
            if not is_delegate:
                raise ValidationError({'role': 'Only an existing delegate can be promoted to manager.'})
            previous_manager = opportunity.manager
            opportunity.delegates.remove(member)
            opportunity.manager = member
            opportunity.save(update_fields=['manager', 'modified_at'])
            opportunity.delegates.add(previous_manager)
            return Response(OpportunityMemberSerializer(_opportunity_members(opportunity), many=True).data)

        if not (is_delegate or is_stakeholder):
            raise NotFound('This user is not a member of the opportunity.')
        opportunity.delegates.remove(member)
        opportunity.stakeholders.remove(member)
        if new_role == 'delegate':
            opportunity.delegates.add(member)
        else:
            opportunity.stakeholders.add(member)
        return Response(OpportunityMemberSerializer(_opportunity_members(opportunity), many=True).data)


class ProjectViewSet(ProjectAncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        queryset = Project.objects.filter(
            opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related('opportunity')
        opportunity_pk = self.kwargs.get('opportunity_pk')
        if opportunity_pk is not None:
            queryset = queryset.filter(opportunity_id=opportunity_pk)
        return queryset

    def get_serializer_context(self):
        # For the nested list route, resolving the ancestor (and 404ing if
        # it's not visible to this user) is what makes `list` 404 for a
        # stranger instead of silently returning an empty array -- same
        # mechanism CommentViewSet relies on.
        context = super().get_serializer_context()
        if 'opportunity_pk' in self.kwargs:
            context['opportunity'] = self.get_ancestor()
        return context

    @action(detail=True, methods=['patch'], url_path='comments-enabled')
    def comments_enabled(self, request, pk=None):
        # Manager-only (of the parent Opportunity), same bar as when this
        # lived on OpportunityViewSet -- stricter than the can_write check
        # OpportunityAccessPermission applies by default, so fetch via the
        # read-scoped queryset and check explicitly.
        project = get_object_or_404(self.get_queryset(), pk=pk)
        if project.get_opportunity().manager_id != request.user.pk:
            raise PermissionDenied('Only the opportunity manager can enable or disable comments.')

        value = request.data.get('comments_enabled')
        if not isinstance(value, bool):
            raise ValidationError({'comments_enabled': 'comments_enabled must be a boolean.'})

        project.comments_enabled = value
        project.save(update_fields=['comments_enabled', 'modified_at'])
        return Response(ProjectSerializer(project).data)


class SiteViewSet(SiteAncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = SiteSerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        queryset = Site.objects.filter(
            project__opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related(
            'project',
            'project__opportunity',
            'project__opportunity__lead_agency',
            'jcode__country_code',
        )
        project_pk = self.kwargs.get('project_pk')
        if project_pk is not None:
            queryset = queryset.filter(project_id=project_pk)
        return queryset

    @action(detail=True, methods=['get'], url_path='available-jcodes')
    def available_jcodes(self, request, pk=None):
        site = self.get_object()
        jcodes = site.get_opportunity().lead_agency.jcodes.select_related('country_code').all()
        return Response(JcodeSerializer(jcodes, many=True).data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if 'project_pk' in self.kwargs:
            context['project'] = self.get_ancestor()
        return context


class StrategyViewSet(
    StrategyAncestorScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    No create/destroy: Strategy rows are auto-provisioned by
    Site.sync_strategies (see list(), below), never added or removed by
    users -- only `selected` and `details` are ever written, via PATCH.
    """

    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        queryset = Strategy.objects.filter(
            site__project__opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related(
            'site',
            'site__project',
            'site__project__opportunity',
            'intervention_type',
            'intervention_type__cmf',
            'intervention_type__cmf__metadata',
        ).prefetch_related('intervention_type__cmf__coefficients')
        site_pk = self.kwargs.get('site_pk')
        if site_pk is not None:
            queryset = queryset.filter(site_id=site_pk)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if 'site_pk' in self.kwargs:
            context['site'] = self.get_ancestor()
        return context

    def list(self, request, *args, **kwargs):
        if 'site_pk' in self.kwargs:
            self.get_ancestor().sync_strategies()
        return super().list(request, *args, **kwargs)
