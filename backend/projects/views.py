from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from analysis.serializers import ProjectionSerializer
from analysis.services import run_stub_analysis

from .cloning import clone_course_of_action, clone_intervention, clone_project
from .models import CourseOfAction, Intervention, Project
from .permissions import AncestorScopedMixin, ProjectAccessPermission
from .serializers import (
    CourseOfActionSerializer,
    InterventionSerializer,
    ProjectSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, ProjectAccessPermission]

    def get_queryset(self):
        return (
            Project.objects.visible_to(self.request.user)
            .select_related('focus_area', 'owner')
            .prefetch_related('editors', 'guests')
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        # Cloning only requires read access: it never mutates the source
        # project, only creates a brand-new one owned by the requester.
        project = get_object_or_404(self.get_queryset(), pk=pk)
        cloned = clone_project(project, owner=request.user)
        return Response(ProjectSerializer(cloned).data, status=201)


class CourseOfActionViewSet(AncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = CourseOfActionSerializer
    permission_classes = [permissions.IsAuthenticated, ProjectAccessPermission]

    def get_queryset(self):
        queryset = CourseOfAction.objects.filter(
            project__in=Project.objects.visible_to(self.request.user)
        ).select_related('project', 'projection')
        project_pk = self.kwargs.get('project_pk')
        if project_pk is not None:
            queryset = queryset.filter(project_id=project_pk)
        return queryset

    def get_ancestor(self):
        return get_object_or_404(
            Project.objects.visible_to(self.request.user),
            pk=self.kwargs['project_pk'],
        )

    def get_create_kwargs(self, project):
        return {'project': project}

    def create(self, request, *args, **kwargs):
        if 'project_pk' not in self.kwargs:
            raise ValidationError(
                'A CourseOfAction must be created via '
                '/projects/{project_pk}/courses-of-action/.'
            )
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        # Appends a new sibling row to the existing project, so this
        # requires write access (enforced by ProjectAccessPermission on POST).
        coa = self.get_object()
        cloned = clone_course_of_action(coa)
        return Response(CourseOfActionSerializer(cloned).data, status=201)

    @action(detail=True, methods=['post'], url_path='run-analysis')
    def run_analysis(self, request, pk=None):
        # Mutates the Projection, so this requires write access (enforced by
        # ProjectAccessPermission on POST).
        coa = self.get_object()
        result = run_stub_analysis(coa)
        projection = coa.projection
        projection.result_data = result
        projection.status = projection.Status.COMPLETE
        projection.computed_at = timezone.now()
        projection.save(update_fields=['result_data', 'status', 'computed_at', 'modified_at'])
        return Response(ProjectionSerializer(projection).data)


class InterventionViewSet(AncestorScopedMixin, viewsets.ModelViewSet):
    serializer_class = InterventionSerializer
    permission_classes = [permissions.IsAuthenticated, ProjectAccessPermission]

    def get_queryset(self):
        queryset = Intervention.objects.filter(
            course_of_action__project__in=Project.objects.visible_to(self.request.user)
        ).select_related('course_of_action__project', 'intervention_type')
        coa_pk = self.kwargs.get('coa_pk')
        if coa_pk is not None:
            queryset = queryset.filter(course_of_action_id=coa_pk)
        return queryset

    def get_ancestor(self):
        return get_object_or_404(
            CourseOfAction.objects.filter(
                project__in=Project.objects.visible_to(self.request.user)
            ),
            pk=self.kwargs['coa_pk'],
        )

    def get_create_kwargs(self, coa):
        return {'course_of_action': coa}

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if 'coa_pk' in self.kwargs:
            context['course_of_action'] = self.get_ancestor()
        return context

    def create(self, request, *args, **kwargs):
        if 'coa_pk' not in self.kwargs:
            raise ValidationError(
                'An Intervention must be created via '
                '/courses-of-action/{coa_pk}/interventions/.'
            )
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        intervention = self.get_object()
        cloned = clone_intervention(intervention)
        return Response(InterventionSerializer(cloned).data, status=201)
