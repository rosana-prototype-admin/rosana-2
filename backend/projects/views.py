from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import User
from analysis.serializers import ProjectionSerializer
from analysis.services import run_stub_analysis

from .cloning import clone_opportunity, clone_project, clone_strategy
from .models import Intervention, Opportunity, Organization, Project, Strategy
from .permissions import AncestorScopedMixin, OpportunityAccessPermission, can_invite, can_manage_roles
from .services import sync_compatible_interventions
from .serializers import (
    ChangeMemberRoleSerializer,
    InterventionSerializer,
    InviteMemberSerializer,
    OpportunityMemberSerializer,
    OpportunitySerializer,
    OrganizationSerializer,
    ProjectSerializer,
    StrategySerializer,
)


def _opportunity_members(opportunity):
    """Flatten owner + editors + guests into one role-tagged list."""
    def _entry(user, role):
        return {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': role,
        }

    members = [_entry(opportunity.owner, 'owner')]
    members += [_entry(user, 'editor') for user in opportunity.editors.all()]
    members += [_entry(user, 'guest') for user in opportunity.guests.all()]
    return members


class OpportunityViewSet(viewsets.ModelViewSet):
    serializer_class = OpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        return (
            Opportunity.objects.visible_to(self.request.user)
            .select_related('focus_area', 'owner')
            .prefetch_related('editors', 'guests')
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        # Cloning only requires read access: it never mutates the source
        # opportunity, only creates a brand-new one owned by the requester.
        opportunity = get_object_or_404(self.get_queryset(), pk=pk)
        cloned = clone_opportunity(opportunity, owner=request.user)
        return Response(OpportunitySerializer(cloned).data, status=201)

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        if request.method == 'POST':
            # Inviting is owner-only (can_invite), which is stricter than the
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

        # GET: any read access (owner/editor/guest) may view the member list.
        opportunity = self.get_object()
        return Response(OpportunityMemberSerializer(_opportunity_members(opportunity), many=True).data)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'members/(?P<user_id>\d+)')
    def member_detail(self, request, pk=None, user_id=None):
        opportunity = get_object_or_404(self.get_queryset(), pk=pk)
        if not can_manage_roles(request.user, opportunity):
            raise PermissionDenied("You do not have permission to manage this opportunity's members.")

        is_editor = opportunity.editors.filter(pk=user_id).exists()
        is_guest = opportunity.guests.filter(pk=user_id).exists()
        if not (is_editor or is_guest):
            raise NotFound('This user is not a member of the opportunity.')
        member = get_object_or_404(User, pk=user_id)

        if request.method == 'DELETE':
            opportunity.editors.remove(member)
            opportunity.guests.remove(member)
            return Response(status=204)

        serializer = ChangeMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opportunity.editors.remove(member)
        opportunity.guests.remove(member)
        if serializer.validated_data['role'] == 'editor':
            opportunity.editors.add(member)
        else:
            opportunity.guests.add(member)
        return Response(OpportunityMemberSerializer(_opportunity_members(opportunity), many=True).data)


class StrategyViewSet(AncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        queryset = Strategy.objects.filter(
            opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related('opportunity', 'projection')
        opportunity_pk = self.kwargs.get('opportunity_pk')
        if opportunity_pk is not None:
            queryset = queryset.filter(opportunity_id=opportunity_pk)
        return queryset

    def get_ancestor(self):
        return get_object_or_404(
            Opportunity.objects.visible_to(self.request.user),
            pk=self.kwargs['opportunity_pk'],
        )

    def get_create_kwargs(self, opportunity):
        return {'opportunity': opportunity}

    def create(self, request, *args, **kwargs):
        if 'opportunity_pk' not in self.kwargs:
            raise ValidationError(
                'A Strategy must be created via '
                '/opportunities/{opportunity_pk}/strategies/.'
            )
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        # Appends a new sibling row to the existing opportunity, so this
        # requires write access (enforced by OpportunityAccessPermission on POST).
        strategy = self.get_object()
        cloned = clone_strategy(strategy)
        return Response(StrategySerializer(cloned).data, status=201)

    @action(detail=True, methods=['post'], url_path='run-analysis')
    def run_analysis(self, request, pk=None):
        # Mutates the Projection, so this requires write access (enforced by
        # OpportunityAccessPermission on POST).
        strategy = self.get_object()
        result = run_stub_analysis(strategy)
        projection = strategy.projection
        projection.result_data = result
        projection.status = projection.Status.COMPLETE
        projection.computed_at = timezone.now()
        projection.save(update_fields=['result_data', 'status', 'computed_at', 'modified_at'])
        return Response(ProjectionSerializer(projection).data)


class InterventionViewSet(AncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = InterventionSerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        queryset = Intervention.objects.filter(
            strategy__opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related('strategy__opportunity', 'intervention_type', 'project')
        strategy_pk = self.kwargs.get('strategy_pk')
        if strategy_pk is not None:
            queryset = queryset.filter(strategy_id=strategy_pk)
        return queryset

    def get_ancestor(self):
        return get_object_or_404(
            Strategy.objects.filter(
                opportunity__in=Opportunity.objects.visible_to(self.request.user)
            ),
            pk=self.kwargs['strategy_pk'],
        )

    def get_create_kwargs(self, strategy):
        return {'strategy': strategy}

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if 'strategy_pk' in self.kwargs:
            context['strategy'] = self.get_ancestor()
        return context

    def list(self, request, *args, **kwargs):
        if 'strategy_pk' in self.kwargs:
            # Backfill one Intervention per InterventionType compatible with
            # the Strategy's Opportunity focus area before listing, so the
            # table always reflects the full compatible set (see
            # sync_compatible_interventions).
            sync_compatible_interventions(self.get_ancestor())
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if 'strategy_pk' not in self.kwargs:
            raise ValidationError(
                'An Intervention must be created via '
                '/strategies/{strategy_pk}/interventions/.'
            )
        return super().create(request, *args, **kwargs)


class ProjectViewSet(AncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, OpportunityAccessPermission]

    def get_queryset(self):
        queryset = Project.objects.filter(
            strategy__opportunity__in=Opportunity.objects.visible_to(self.request.user)
        ).select_related('strategy__opportunity').prefetch_related(
            'organizations', 'interventions__intervention_type'
        )
        strategy_pk = self.kwargs.get('strategy_pk')
        if strategy_pk is not None:
            queryset = queryset.filter(strategy_id=strategy_pk)
        return queryset

    def get_ancestor(self):
        return get_object_or_404(
            Strategy.objects.filter(
                opportunity__in=Opportunity.objects.visible_to(self.request.user)
            ),
            pk=self.kwargs['strategy_pk'],
        )

    def get_create_kwargs(self, strategy):
        return {'strategy': strategy}

    def create(self, request, *args, **kwargs):
        if 'strategy_pk' not in self.kwargs:
            raise ValidationError(
                'A Project must be created via '
                '/strategies/{strategy_pk}/projects/.'
            )
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        # Appends a new sibling row to the existing strategy, so this
        # requires write access (enforced by OpportunityAccessPermission on POST).
        project = self.get_object()
        cloned = clone_project(project)
        return Response(ProjectSerializer(cloned).data, status=201)


class OrganizationViewSet(viewsets.ModelViewSet):
    """A shared, freeform catalog of organizations any authenticated user may search or add to."""

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset
