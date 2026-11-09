from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .email import send_verification_email
from groups.models import Group

from .models import Contract, SubscriptionSeat, User, UserSubscription
from .password_reset import send_password_reset_email
from .permissions import IsPlatformAdmin
from .serializers import (
    AdminContractSerializer,
    AdminGroupSerializer,
    AdminSubscriptionSeatSerializer,
    AdminSubscriptionSerializer,
    AdminUserSerializer,
)


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


class AdminGroupListView(generics.ListAPIView):
    serializer_class = AdminGroupSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        queryset = Group.objects.select_related('admin').all()
        query = self.request.query_params.get('q', '').strip()
        return queryset.filter(name__icontains=query) if query else queryset


class AdminGroupSubscriptionView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminSubscriptionSerializer
    permission_classes = [IsPlatformAdmin]

    def get_object(self):
        group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        subscription = group.subscriptions.order_by('-starts_at', '-created_at').first()
        if subscription is None:
            subscription = UserSubscription.objects.create(
                group=group,
                plan_code='none',
                starts_at=timezone.now(),
            )
        return subscription


class AdminGroupContractListCreateView(generics.ListCreateAPIView):
    serializer_class = AdminContractSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return Contract.objects.filter(group_id=self.kwargs['group_pk'])

    def perform_create(self, serializer):
        group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        serializer.save(group=group)


class AdminGroupContractDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminContractSerializer
    permission_classes = [IsPlatformAdmin]
    lookup_url_kwarg = 'contract_pk'

    def get_queryset(self):
        return Contract.objects.filter(group_id=self.kwargs['group_pk'])


class AdminGroupSeatListCreateView(generics.ListCreateAPIView):
    serializer_class = AdminSubscriptionSeatSerializer
    permission_classes = [IsPlatformAdmin]

    def get_subscription(self):
        group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        return group.subscriptions.order_by('-starts_at', '-created_at').first()

    def get_queryset(self):
        subscription = self.get_subscription()
        return SubscriptionSeat.objects.filter(subscription=subscription, released_at__isnull=True) if subscription else SubscriptionSeat.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['subscription'] = self.get_subscription()
        return context

    def perform_create(self, serializer):
        subscription = self.get_subscription()
        if subscription is None:
            raise serializers.ValidationError({'detail': 'Create a subscription before assigning seats.'})
        if subscription.seats.filter(released_at__isnull=True).count() >= subscription.seat_limit:
            raise serializers.ValidationError({'detail': 'This subscription has no available seats.'})
        serializer.save(subscription=subscription)


class AdminGroupSeatDetailView(generics.DestroyAPIView):
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return SubscriptionSeat.objects.filter(subscription__group_id=self.kwargs['group_pk'], released_at__isnull=True)

    def perform_destroy(self, instance):
        instance.released_at = timezone.now()
        instance.save(update_fields=['released_at'])
