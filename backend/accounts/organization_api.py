from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from groups.models import Group, Membership, RosanaRole

from .audit import record_admin_event
from .entitlements import can_change_billing, can_manage_seats, can_view_billing
from .models import Plan, SubscriptionSeat, UserSubscription
from .serializers import AdminSubscriptionSeatSerializer, OrganizationSubscriptionSerializer, UserSearchResultSerializer


def organization_for_request(request, group_pk):
    group = get_object_or_404(Group, pk=group_pk)
    organization = group
    while organization.parent_id is not None:
        organization = organization.parent
    is_member = organization.effective_members().filter(pk=request.user.pk).exists()
    if not can_view_billing(request.user, organization) and not is_member:
        raise PermissionDenied('You do not have permission to view this organization subscription.')
    return organization


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
            'can_view_billing': can_view_billing(request.user, group),
            'can_change_subscription': can_change_billing(request.user, group),
            'can_manage_seats': can_manage_seats(request.user, group),
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
                seat.user_id: seat
                for seat in SubscriptionSeat.objects.filter(
                    subscription=subscription, released_at__isnull=True
                )
            }
        users = []
        for user in group.effective_members().order_by('username'):
            entry = UserSearchResultSerializer(user).data
            seat = seats.get(user.pk)
            entry['seat_id'] = seat.pk if seat else None
            entry['seat_type'] = seat.seat_type if seat else None
            membership = Membership.objects.filter(group=group, user=user).first()
            entry['rosana_role'] = membership.rosana_role if membership else RosanaRole.TECHNICAL_ADMIN
            users.append(entry)
        return Response({
            'organization': {'id': group.id, 'name': group.name},
            'subscription_id': subscription.pk if subscription else None,
            'can_manage_seats': can_manage_seats(request.user, group),
            'users': users,
        })


class OrganizationSubscriptionSeatListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_pk):
        group = organization_for_request(request, group_pk)
        if not can_manage_seats(request.user, group):
            return Response(
                {'detail': 'Only a Technical Admin may assign seats.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        subscription = group.subscriptions.order_by('-starts_at', '-created_at').first()
        if subscription is None:
            raise serializers.ValidationError({'detail': 'Create a subscription before assigning seats.'})
        if subscription.seats.filter(released_at__isnull=True).count() >= subscription.seat_limit:
            raise serializers.ValidationError({'detail': 'This subscription has no available seats.'})
        serializer = AdminSubscriptionSeatSerializer(
            data=request.data, context={'subscription': subscription}
        )
        serializer.is_valid(raise_exception=True)
        seat = serializer.save(subscription=subscription)
        record_admin_event(
            request, 'seat.assigned', seat,
            after=AdminSubscriptionSeatSerializer(seat).data,
            group=group,
        )
        return Response(AdminSubscriptionSeatSerializer(seat).data, status=status.HTTP_201_CREATED)


class OrganizationSubscriptionSeatDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, group_pk, seat_pk):
        group = organization_for_request(request, group_pk)
        if not can_manage_seats(request.user, group):
            return Response(
                {'detail': 'Only a Technical Admin may release seats.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        organization_subscription_ids = group.subscriptions.values_list('id', flat=True)
        seat = get_object_or_404(
            SubscriptionSeat,
            pk=seat_pk,
            subscription_id__in=organization_subscription_ids,
            released_at__isnull=True,
        )
        before = AdminSubscriptionSeatSerializer(seat).data
        seat.released_at = timezone.now()
        seat.save(update_fields=['released_at'])
        record_admin_event(
            request, 'seat.released', seat,
            before=before,
            after=AdminSubscriptionSeatSerializer(seat).data,
            group=group,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
