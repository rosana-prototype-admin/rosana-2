from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .email import send_verification_email
from .models import User
from .password_reset import send_password_reset_email
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


class AdminResendVerificationView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.email_verified:
            return Response(
                {'detail': 'This account already has a verified email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        send_verification_email(user)
        return Response({'detail': 'A new verification email has been sent.'})


class AdminSendPasswordResetView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if not user.is_active or not user.email_verified:
            return Response(
                {'detail': 'Password reset email requires an active, verified account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        send_password_reset_email(user)
        return Response({'detail': 'A password reset email has been sent.'})
