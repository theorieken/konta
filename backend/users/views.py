"""Authentication and user management."""

from __future__ import annotations

from decimal import Decimal
import logging

from django.db import transaction
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from base.authentication import issue_token
from base.permissions import IsAuthenticatedHousehold, IsSelfOrStaff
from base.households import active_household
from base.settings_registry import (
    CURRENCY,
    PREDICTION_HORIZON_MONTHS,
    SAVINGS_GOAL,
    SAVINGS_GOAL_DATE,
)
from base.views import BaseViewSet
from users.models import User
from users.serializers import (
    ChangePasswordSerializer,
    InviteUserSerializer,
    LoginSerializer,
    OnboardingSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
)
from users.services import EmailDeliveryError, send_password_link

logger = logging.getLogger(__name__)


class AuthStatusView(APIView):
    """
    `/api/auth/status/` – the very first call the frontend makes.

    Tells the client whether it has to show the onboarding wizard, the login
    page or the app.
    """

    permission_classes = [AllowAny]
    authentication_classes = APIView.authentication_classes

    def get(self, request) -> Response:
        from base.models import Setting

        user_count = User.objects.count()
        authenticated = bool(request.user and request.user.is_authenticated)
        household = active_household(request.user) if authenticated else None
        return Response(
            {
                "needs_onboarding": user_count == 0,
                "user_count": user_count,
                "authenticated": authenticated,
                "user": UserSerializer(request.user).data if authenticated else None,
                "household_name": household.name if household else "Mein Haushalt",
                "current_household": str(household.pk) if household else None,
                "households": [
                    {"id": str(entry.pk), "name": entry.name}
                    for entry in request.user.households.all()
                ] if authenticated else [],
                "currency": Setting.get(CURRENCY, "EUR", household=household),
            }
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    # A stale client token must never prevent starting a new session.
    authentication_classes = []

    def post(self, request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token = issue_token(user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        token = getattr(request, "auth", None)
        if token is not None and hasattr(token, "delete"):
            token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request) -> Response:
        serializer = UserSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.clear_password_link()
        request.user.save(
            update_fields=[
                "password",
                "password_link_token_hash",
                "password_link_purpose",
                "password_link_expires_at",
            ]
        )
        Token.objects.filter(user=request.user).delete()
        token = issue_token(request.user)
        return Response({"token": token.key})


class PasswordResetRequestView(APIView):
    """Send a recovery email without revealing whether an account exists."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email=serializer.validated_data["email"].lower().strip(),
            is_active=True,
        ).first()
        if user is not None:
            try:
                send_password_link(user, User.PasswordLinkPurpose.RESET)
            except EmailDeliveryError:
                logger.exception("Passwort-E-Mail für %s konnte nicht versendet werden", user.pk)
        return Response(
            {"detail": "Wenn ein aktives Konto existiert, wurde eine E-Mail versendet."}
        )


class PasswordResetConfirmView(APIView):
    """Consume a one-time password link and start a fresh session."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = serializer.validated_data["user"]
        raw_token = serializer.validated_data["token"]

        with transaction.atomic():
            user = User.all_objects.select_for_update().get(pk=candidate.pk)
            if not user.password_link_is_valid(raw_token):
                raise ValidationError({"detail": "Dieser Link ist ungültig oder abgelaufen."})
            user.set_password(serializer.validated_data["new_password"])
            user.is_active = True
            user.is_onboarded = True
            user.clear_password_link()
            user.save(
                update_fields=[
                    "password",
                    "is_active",
                    "is_onboarded",
                    "password_link_token_hash",
                    "password_link_purpose",
                    "password_link_expires_at",
                    "updated_at",
                ]
            )
            Token.objects.filter(user=user).delete()
            token = issue_token(user)

        return Response({"token": token.key, "user": UserSerializer(user).data})


class OnboardingView(APIView):
    """
    `/api/auth/onboarding/` – creates the first user, the household settings
    and the initial accounts. Refuses to run once a user exists.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request) -> Response:
        if User.objects.exists():
            return Response(
                {"detail": "Das Onboarding wurde bereits abgeschlossen.", "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = User.objects.create_superuser(
                email=data["email"],
                password=data["password"],
                name=data["name"],
                is_onboarded=True,
            )

            from base.models import Household, Setting
            from finance.models import Account

            household = Household.objects.filter(members__isnull=True).first()
            if household is None:
                household = Household.objects.create(
                    name=data.get("household_name") or "Mein Haushalt", created_by=user
                )
            else:
                household.name = data.get("household_name") or household.name
                household.created_by = household.created_by or user
                household.save(update_fields=["name", "created_by", "updated_at"])
            user.households.add(household)
            user.current_household = household
            user.save(update_fields=["current_household", "updated_at"])

            if data.get("currency"):
                Setting.set(CURRENCY, data["currency"].upper(), user=user, household=household)
            if data.get("prediction_horizon_months"):
                Setting.set(PREDICTION_HORIZON_MONTHS, data["prediction_horizon_months"], user=user, household=household)
            if data.get("savings_goal") is not None:
                Setting.set(SAVINGS_GOAL, float(data["savings_goal"]), user=user, household=household)
            if data.get("savings_goal_date"):
                Setting.set(SAVINGS_GOAL_DATE, data["savings_goal_date"].isoformat(), user=user, household=household)

            for entry in data.get("accounts") or []:
                Account.objects.create(
                    name=entry["name"],
                    holder=entry.get("holder", ""),
                    opening_balance=Decimal(str(entry.get("opening_balance") or 0)),
                    household=household,
                    created_by=user,
                )

            # Standard categories are idempotent – safe to call again here.
            from finance.services.seed import ensure_default_categories

            ensure_default_categories(user=user, household=household)

        token = issue_token(user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class UserViewSet(BaseViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedHousehold, IsSelfOrStaff]
    search_fields = ["name", "email", "first_name", "last_name"]
    ordering_fields = ["name", "email", "created_at"]

    def create(self, request, *args, **kwargs) -> Response:
        if not request.user.is_staff:
            raise PermissionDenied("Nur Administratoren dürfen Benutzer anlegen.")
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request) -> Response:
        return Response(self.get_serializer(request.user).data)

    @action(
        detail=False,
        methods=["post"],
        url_path="invite",
        permission_classes=[IsAdminUser],
    )
    def invite(self, request) -> Response:
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.filter(email=data["email"]).first()
        if user is None:
            user = User.objects.create_user(
                email=data["email"],
                password=None,
                name=data["name"],
                is_active=False,
                is_onboarded=True,
                created_by=request.user,
            )
        else:
            user.name = data["name"]
            user.save(update_fields=["name", "updated_at"])
        household = active_household(request.user)
        user.households.add(household)
        if user.current_household_id is None:
            user.current_household = household
            user.save(update_fields=["current_household", "updated_at"])
        try:
            send_password_link(user, User.PasswordLinkPurpose.INVITATION)
        except EmailDeliveryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="password-link",
        permission_classes=[IsAdminUser],
    )
    def password_link(self, request, *args, **kwargs) -> Response:
        user = self.get_object()
        purpose = (
            User.PasswordLinkPurpose.RESET
            if user.is_active
            else User.PasswordLinkPurpose.INVITATION
        )
        try:
            send_password_link(user, purpose)
        except EmailDeliveryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"detail": "Link wurde per E-Mail versendet."})
