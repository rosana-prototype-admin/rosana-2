from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import CrashCasualtyConversionTable
from .serializers import CrashCasualtyConversionTableSerializer


class CrashCasualtyConversionTableViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only reference data for the analysis pipeline."""

    queryset = CrashCasualtyConversionTable.objects.select_related('country_code').prefetch_related('rows')
    serializer_class = CrashCasualtyConversionTableSerializer

    @action(detail=False, methods=['get'])
    def resolve(self, request):
        year = request.query_params.get('year')
        if year is None:
            raise ValidationError({'year': 'An analysis year is required.'})

        try:
            year = int(year)
        except ValueError as exc:
            raise ValidationError({'year': 'Year must be an integer.'}) from exc

        table = CrashCasualtyConversionTable.objects.resolve_for_analysis(
            year,
            country_code=request.query_params.get('country_code', 'US'),
            region_code=request.query_params.get('region_code'),
            version=request.query_params.get('version'),
        )
        if table is None:
            return Response({'detail': 'No conversion table covers the requested inputs.'}, status=404)
        return Response(self.get_serializer(table).data)
