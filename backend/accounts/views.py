from django.db.models import Q
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .email import send_verification_email
from .models import User
from .password_reset import send_password_reset_email
from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSearchResultSerializer,
    UserSerializer,
)
from .tokens import email_verification_token


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email(user)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'detail': 'This verification link is invalid or expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not email_verification_token.check_token(user, token):
            return Response(
                {'detail': 'This verification link is invalid or expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email_verified = True
        user.is_active = True
        user.save(update_fields=['email_verified', 'is_active'])
        return Response({'detail': 'Your email has been verified. You can now sign in.'})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(
            email__iexact=email,
            is_active=True,
            email_verified=True,
        ).first()
        if user:
            send_password_reset_email(user)
        return Response({
            'detail': 'If an account exists for that email, a password reset link has been sent.'
        })


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'detail': 'This password reset link is invalid or expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'This password reset link is invalid or expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PasswordResetConfirmSerializer(
            data=request.data,
            context={'user': user},
        )
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Your password has been reset. You can now sign in.'})


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserSearchView(generics.ListAPIView):
    """
    Directory search for finding users to invite: GET /api/auth/users/?q=&jcode=

    - `q` matches (case-insensitive, partial) against username, email, first
      or last name. Requires at least MIN_QUERY_LENGTH characters.
    - `jcode` filters to users affiliated with a group that has that Jcode
      assigned (Jcode's primary key is the Census place code string, e.g.
      "US1900000000", not an integer). Naturally bounded (a jurisdiction's
      user list is small), so it's allowed on its own.
    - Neither param -> empty result, not the full user directory.
    """

    serializer_class = UserSearchResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    MIN_QUERY_LENGTH = 2
    MAX_RESULTS = 20

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        jcode = self.request.query_params.get('jcode', '').strip()

        if not query and not jcode:
            return User.objects.none()

        queryset = User.objects.all()

        if jcode:
            queryset = queryset.filter(
                Q(administered_groups__jcodes__id=jcode)
                | Q(memberships__group__jcodes__id=jcode)
            )

        if query:
            if len(query) < self.MIN_QUERY_LENGTH:
                return User.objects.none()
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )

        return queryset.distinct().order_by('username')[: self.MAX_RESULTS]
