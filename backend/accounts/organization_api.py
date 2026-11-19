from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from groups.models import Group

from .audit import record_admin_event
from .entitlements import can_change_billing, can_view_billing
from .models import Plan, SubscriptionSeat, UserSubscription
from .serializers import OrganizationSubscriptionSerializer, UserSearchResultSerializer


def organization_for_request(request, group_pk):
    group = get_object_or_404(Group, pk=group_pk, parent__isnull=True)
    if not can_view_billing(request.user, group):
        raise PermissionDenied('You do not have permission to view this organization subscription.')
    return group


class OrganizationSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_pk):
        group = organization_for_request(request, group_pk)
        subscription = group.subscriptions.select_related('plan').order_by('-starts_at', '-created_at').first()
        plans = Plan.objects.filter(active=True, self_service_visible=True).values(
            'id', 'code', 'name', 'description'
        )
        return Response({
            'organization': {'id': group.id, 'name': group.name},
            'subscription': OrganizationSubscriptionSerializer(subscription).data if subscription else None,
            'plans': list(plans),
            'can_change_subscription': can_change_billing(request.user, group),
            'payment_processing': 'not_configured',
        })

    def patch(self, request, group_pk):
        group = organization_for_request(request, group_pk)
        if not can_change_billing(request.user, group):
            return Response(
                {'detail': 'Only a Financial Admin may change this subscription.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        subscription = group.subscriptions.order_by('-starts_at', '-created_at').first()
        if subscription is None:
            if 'plan_id' not in request.data:
                raise serializers.ValidationError({'plan_id': 'A plan is required to create a subscription.'})
            subscription = UserSubscription(
                group=group,
                plan_code='none',
                status='active',
                starts_at=timezone.now(),
                seat_limit=1,
            )
        before = OrganizationSubscriptionSerializer(subscription).data if subscription.pk else {}
        serializer = OrganizationSubscriptionSerializer(
            subscription, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save(group=group)
        after = OrganizationSubscriptionSerializer(updated).data
        if before != after:
            record_admin_event(
                request, 'organization.subscription_updated', updated,
                before=before, after=after, group=group,
            )
        return Response(after)


class OrganizationSubscriptionUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_pk):
        group = organization_for_request(request, group_pk)
        subscription = group.subscriptions.order_by('-starts_at', '-created_at').first()
        seats = {}
        if subscription is not None:
            seats = {
                seat.user_id: seat.seat_type
                for seat in SubscriptionSeat.objects.filter(
                    subscription=subscription, released_at__isnull=True
                )
            }
        users = []
        for user in group.effective_members().order_by('username'):
            entry = UserSearchResultSerializer(user).data
            entry['seat_type'] = seats.get(user.pk)
            users.append(entry)
        return Response({
            'organization': {'id': group.id, 'name': group.name},
            'subscription_id': subscription.pk if subscription else None,
            'users': users,
        })
