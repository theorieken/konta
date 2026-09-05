from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import (
    AuthStatusView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    OnboardingView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/status/", AuthStatusView.as_view(), name="auth-status"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/password/", ChangePasswordView.as_view(), name="auth-password"),
    path(
        "auth/password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("auth/onboarding/", OnboardingView.as_view(), name="auth-onboarding"),
    path("", include(router.urls)),
]
