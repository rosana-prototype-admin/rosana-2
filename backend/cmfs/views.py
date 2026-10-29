from django.db import models
from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import CMF, CMFUserPermission
from .config import CMF_FILTER_CONFIG, CMF_LOWER_LIMIT, CMF_MATH_CONFIG, CMF_MOD_CODE_OPTIONS, CMF_UPPER_LIMIT
from .permissions import CMFAccessPermission
from .serializers import CMFSerializer


class CMFViewSet(viewsets.ModelViewSet):
    serializer_class = CMFSerializer
    permission_classes = [permissions.IsAuthenticated, CMFAccessPermission]

    def get_queryset(self):
        plan_field = CMFUserPermission.field_for_user(self.request.user)
        if plan_field:
            builtin_visibility = (
                Q(is_builtin=True, user_permissions__isnull=True)
                | Q(is_builtin=True, **{f'user_permissions__{plan_field}': True})
            )
        else:
            builtin_visibility = Q(is_builtin=True, user_permissions__isnull=True)
        return CMF.objects.filter(
            builtin_visibility
            | models.Q(is_builtin=False)
        ).select_related('author', 'base_cmf').prefetch_related(
            'permitted_groups', 'coefficients', 'user_permissions'
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get'])
    def resolve(self, request):
        code = request.query_params.get('code', '').strip()
        if not code:
            raise ValidationError({'code': 'A CMF code is required.'})
        cmf = CMF.resolve_for_user(code, request.user)
        if cmf is None:
            return Response({'detail': 'No CMF exists for this code.'}, status=404)
        return Response(self.get_serializer(cmf).data)

    @action(detail=False, methods=['get'])
    def config(self, request):
        return Response({
            'cmf_lower_limit': float(CMF_LOWER_LIMIT),
            'cmf_upper_limit': float(CMF_UPPER_LIMIT),
            'cmf_filters': CMF_FILTER_CONFIG,
            'cmf_math': CMF_MATH_CONFIG,
            'cmf_mod_codes': CMF_MOD_CODE_OPTIONS,
        })
