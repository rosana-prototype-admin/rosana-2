from django.db.models import Q
from rest_framework import generics

from .models import User
from .permissions import IsPlatformAdmin
from .serializers import AdminUserSerializer


class AdminUserListView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined', 'username')
        query = self.request.query_params.get('q', '').strip()
        is_active = self.request.query_params.get('is_active')
        email_verified = self.request.query_params.get('email_verified')
        subscription_type = self.request.query_params.get('subscription_type')

        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(company__icontains=query)
            )
        if is_active in {'true', 'false'}:
            queryset = queryset.filter(is_active=is_active == 'true')
        if email_verified in {'true', 'false'}:
            queryset = queryset.filter(email_verified=email_verified == 'true')
        if subscription_type:
            queryset = queryset.filter(subscription_type=subscription_type)
        return queryset


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsPlatformAdmin]
