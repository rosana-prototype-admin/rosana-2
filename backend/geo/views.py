from rest_framework import viewsets

from .models import Jcode
from .serializers import JcodeSerializer


class JcodeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only catalog of jurisdiction codes. Populated via the admin/import tooling."""

    queryset = Jcode.objects.all()
    serializer_class = JcodeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        state = self.request.query_params.get('state')
        if state:
            queryset = queryset.filter(state__iexact=state)
        return queryset
