from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    UserSearchView,
    VerifyEmailView,
)
from .admin_api import (
    AdminResendVerificationView,
    AdminSendPasswordResetView,
    AdminGroupListView,
    AdminGroupSubscriptionView,
    AdminGroupContractListCreateView,
    AdminGroupContractDetailView,
    AdminGroupSeatListCreateView,
    AdminGroupSeatDetailView,
    AdminUserDetailView,
    AdminUserListView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:pk>/resend-verification/', AdminResendVerificationView.as_view(), name='admin-resend-verification'),
    path('admin/users/<int:pk>/send-password-reset/', AdminSendPasswordResetView.as_view(), name='admin-send-password-reset'),
    path('admin/groups/', AdminGroupListView.as_view(), name='admin-group-list'),
    path('admin/groups/<int:group_pk>/subscription/', AdminGroupSubscriptionView.as_view(), name='admin-group-subscription'),
    path('admin/groups/<int:group_pk>/contracts/', AdminGroupContractListCreateView.as_view(), name='admin-group-contract-list'),
    path('admin/groups/<int:group_pk>/contracts/<int:contract_pk>/', AdminGroupContractDetailView.as_view(), name='admin-group-contract-detail'),
    path('admin/groups/<int:group_pk>/seats/', AdminGroupSeatListCreateView.as_view(), name='admin-group-seat-list'),
    path('admin/groups/<int:group_pk>/seats/<int:pk>/', AdminGroupSeatDetailView.as_view(), name='admin-group-seat-detail'),
    path('me/', MeView.as_view(), name='me'),
    path('users/', UserSearchView.as_view(), name='user-search'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
]
