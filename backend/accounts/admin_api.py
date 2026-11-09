from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .email import send_verification_email
from .audit import record_admin_event
from groups.models import Group

from .models import AuditEvent, Contract, SubscriptionSeat, User, UserSubscription
from .password_reset import send_password_reset_email
from .permissions import IsPlatformAdmin
from .serializers import (
    AdminContractSerializer,
    AdminGroupSerializer,
    AdminSubscriptionSeatSerializer,
    AdminSubscriptionSerializer,
    AdminAuditEventSerializer,
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

    def perform_update(self, serializer):
        user = self.get_object()
        before = {field: getattr(user, field) for field in ('is_active', 'email_verified', 'first_name', 'last_name', 'company', 'secondary_email')}
        updated = serializer.save()
        after = {field: getattr(updated, field) for field in before}
        if before != after:
            record_admin_event(self.request, 'user.updated', updated, before, after)


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
        record_admin_event(request, 'user.verification_resent', user)
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
        record_admin_event(request, 'user.password_reset_sent', user)
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

    def perform_update(self, serializer):
        subscription = self.get_object()
        before = AdminSubscriptionSerializer(subscription).data
        updated = serializer.save()
        after = AdminSubscriptionSerializer(updated).data
        if before != after:
            record_admin_event(self.request, 'subscription.updated', updated, before, after, group=updated.group)


class AdminGroupContractListCreateView(generics.ListCreateAPIView):
    serializer_class = AdminContractSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return Contract.objects.filter(group_id=self.kwargs['group_pk'])

    def perform_create(self, serializer):
        group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        contract = serializer.save(group=group)
        record_admin_event(self.request, 'contract.created', contract, after=AdminContractSerializer(contract).data, group=group)


class AdminGroupContractDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminContractSerializer
    permission_classes = [IsPlatformAdmin]
    lookup_url_kwarg = 'contract_pk'

    def get_queryset(self):
        return Contract.objects.filter(group_id=self.kwargs['group_pk'])

    def perform_update(self, serializer):
        contract = self.get_object()
        before = AdminContractSerializer(contract).data
        updated = serializer.save()
        after = AdminContractSerializer(updated).data
        if before != after:
            record_admin_event(self.request, 'contract.updated', updated, before, after, group=updated.group)


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
        seat = serializer.save(subscription=subscription)
        record_admin_event(self.request, 'seat.assigned', seat, after=AdminSubscriptionSeatSerializer(seat).data, group=subscription.group)


class AdminGroupSeatDetailView(generics.DestroyAPIView):
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return SubscriptionSeat.objects.filter(subscription__group_id=self.kwargs['group_pk'], released_at__isnull=True)

    def perform_destroy(self, instance):
        before = AdminSubscriptionSeatSerializer(instance).data
        instance.released_at = timezone.now()
        instance.save(update_fields=['released_at'])
        record_admin_event(self.request, 'seat.released', instance, before, AdminSubscriptionSeatSerializer(instance).data, group=instance.subscription.group)


class AdminAuditEventListView(generics.ListAPIView):
    serializer_class = AdminAuditEventSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related('actor', 'group').all()
        action = self.request.query_params.get('action')
        entity_type = self.request.query_params.get('entity_type')
        group_id = self.request.query_params.get('group_id')
        if action:
            queryset = queryset.filter(action=action)
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset[:200]
