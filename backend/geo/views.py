from django.db.models import Q
from rest_framework import viewsets

from .models import CountryCode, Jcode
from .serializers import CountryCodeSerializer, JcodeSerializer


class CountryCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only catalog of ISO 3166-1 country codes. Populated via migration."""

    queryset = CountryCode.objects.all()
    serializer_class = CountryCodeSerializer


class JcodeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only catalog of jurisdiction codes. Populated via the admin/import tooling."""

    queryset = Jcode.objects.select_related('country_code')
    serializer_class = JcodeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        state = self.request.query_params.get('state')
        if state:
            queryset = queryset.filter(state__iexact=state)
        county = self.request.query_params.get('county')
        if county:
            queryset = queryset.filter(county__iexact=county)
        search = self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search)
                | Q(state__icontains=search)
                | Q(county__icontains=search)
                | Q(place_name_short__icontains=search)
                | Q(place_name_long__icontains=search)
                | Q(census_place_name__icontains=search)
            )
        return queryset
