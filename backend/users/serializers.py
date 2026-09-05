from __future__ import annotations

from typing import Any

from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers

from base.serializers import BaseSerializer, register_serializer
from users.models import User


@register_serializer
class UserSerializer(BaseSerializer):
    initials = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    current_household = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = User
        fields = BaseSerializer.BASE_FIELDS + (
            "email",
            "first_name",
            "last_name",
            "color",
            "initials",
            "display_name",
            "is_active",
            "is_staff",
            "is_onboarded",
            "last_login",
            "current_household",
            "password",
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS + (
            "is_staff",
            "last_login",
            "initials",
            "display_name",
        )

    def validate_password(self, value: str) -> str:
        if value:
            password_validation.validate_password(value)
        return value

    def create(self, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password", "") or None
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password", "")
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"].lower().strip(),
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError(
                {"detail": "E-Mail-Adresse oder Passwort ist falsch."}
            )
        if not user.is_active:
            raise serializers.ValidationError({"detail": "Dieses Konto ist deaktiviert."})
        attrs["user"] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Das aktuelle Passwort ist falsch.")
        return value

    def validate_new_password(self, value: str) -> str:
        password_validation.validate_password(value, self.context["request"].user)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, min_length=32)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        token_hash = User.password_link_hash(attrs["token"])
        user = User.all_objects.filter(
            password_link_token_hash=token_hash,
            deleted_at__isnull=True,
        ).first()
        if user is None or not user.password_link_is_valid(attrs["token"]):
            raise serializers.ValidationError(
                {"detail": "Dieser Link ist ungültig oder abgelaufen."}
            )
        password_validation.validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs


class InviteUserSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        email = value.lower().strip()
        existing = User.all_objects.filter(email=email).first()
        if existing is not None and (existing.is_active or existing.has_usable_password()):
            raise serializers.ValidationError("Diese E-Mail-Adresse ist bereits vergeben.")
        if existing is not None and existing.deleted_at is not None:
            raise serializers.ValidationError("Für diese E-Mail-Adresse existiert ein gelöschtes Konto.")
        return email


class OnboardingAccountSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    holder = serializers.CharField(max_length=255, required=False, allow_blank=True)
    opening_balance = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0
    )


class OnboardingSerializer(serializers.Serializer):
    """
    First run wizard. Only accepted while no user exists – afterwards the
    endpoint returns 403 and the frontend shows the login page instead.
    """

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    household_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    currency = serializers.CharField(max_length=8, required=False, allow_blank=True)
    prediction_horizon_months = serializers.IntegerField(required=False, min_value=1, max_value=600)
    savings_goal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    savings_goal_date = serializers.DateField(required=False, allow_null=True)
    accounts = OnboardingAccountSerializer(many=True, required=False)

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def validate_email(self, value: str) -> str:
        email = value.lower().strip()
        if User.all_objects.filter(email=email).exists():
            raise serializers.ValidationError("Diese E-Mail-Adresse ist bereits vergeben.")
        return email
