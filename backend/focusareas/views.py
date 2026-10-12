from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import FocusArea, InterventionType
from .serializers import (
    FocusAreaL1L2Serializer,
    FocusAreaSerializer,
    InterventionTypeSerializer,
)


class FocusAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to the Focus Area taxonomy tree. Managed via the admin site."""

    queryset = FocusArea.objects.select_related('parent').all()
    serializer_class = FocusAreaSerializer

    @action(detail=False, url_path='l1-l2')
    def l1_l2(self, request):
        """Combined "L1 - L2" options for the first Opportunity-editor dropdown."""
        nodes = self.get_queryset().filter(level=2)
        serializer = FocusAreaL1L2Serializer(nodes, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def children(self, request, pk=None):
        """Direct children of the selected node, for the second Opportunity-editor dropdown."""
        node = self.get_object()
        children = self.get_queryset().filter(parent=node)
        serializer = FocusAreaSerializer(children, many=True)
        return Response(serializer.data)


class InterventionTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only catalog of intervention types. Managed via the admin site."""

    queryset = InterventionType.objects.prefetch_related('focus_areas').filter(is_active=True)
    serializer_class = InterventionTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        focus_area = self.request.query_params.get('focus_area')
        if focus_area:
            queryset = queryset.filter(focus_areas__id=focus_area)
        return queryset
