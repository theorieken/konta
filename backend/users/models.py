"""The single user model – email + password, token authenticated."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.crypto import constant_time_compare
from django.utils import timezone

from base.models import AllObjectsManager, BaseModel, BaseQuerySet


class UserManager(BaseUserManager):
    """Email based manager that also honours soft deletion."""

    use_in_migrations = True

    def get_queryset(self) -> BaseQuerySet:
        return BaseQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)

    def _create_user(self, email: str, password: str | None, **extra):
        if not email:
            raise ValueError("Eine E-Mail-Adresse ist erforderlich.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("Ein Superuser braucht is_staff und is_superuser.")
        return self._create_user(email, password, **extra)


class User(BaseModel, AbstractUser):
    """
    Household member.

    Everyone who can log in sees the whole household plan – `created_by` is an
    audit trail, not an access boundary (see `base.permissions`).
    """

    username = None  # replaced by email

    class PasswordLinkPurpose(models.TextChoices):
        RESET = "reset", "Passwort zurücksetzen"
        INVITATION = "invitation", "Einladung"

    email = models.EmailField("E-Mail", unique=True, db_index=True)
    households = models.ManyToManyField(
        "base.Household", verbose_name="Haushalte", related_name="members", blank=True
    )
    current_household = models.ForeignKey(
        "base.Household",
        verbose_name="Aktiver Haushalt",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_members",
    )
    color = models.CharField("Farbe", max_length=32, blank=True, default="")
    is_onboarded = models.BooleanField("Onboarding abgeschlossen", default=False)
    password_link_token_hash = models.CharField(
        "Passwort-Link (Hash)", max_length=64, blank=True, default="", db_index=True
    )
    password_link_purpose = models.CharField(
        "Passwort-Link Zweck",
        max_length=16,
        choices=PasswordLinkPurpose.choices,
        blank=True,
        default="",
    )
    password_link_expires_at = models.DateTimeField(
        "Passwort-Link gültig bis", null=True, blank=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "Benutzer"
        verbose_name_plural = "Benutzer"
        ordering = ("name", "email")

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        if not self.name:
            full = f"{self.first_name} {self.last_name}".strip()
            self.name = full or self.email.split("@")[0]
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        return self.name or self.get_full_name() or self.email

    @property
    def initials(self) -> str:
        parts = [part for part in self.display_name.replace(".", " ").split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @staticmethod
    def password_link_hash(token: str) -> str:
        """Hash a password-link token so a database leak cannot expose live links."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue_password_link(self, purpose: str) -> str:
        """Persist a one-time, expiring verifier and return the secret URL token once."""
        token = secrets.token_urlsafe(32)
        ttl = getattr(settings, "PASSWORD_LINK_TTL", timedelta(hours=24))
        self.password_link_token_hash = self.password_link_hash(token)
        self.password_link_purpose = purpose
        self.password_link_expires_at = timezone.now() + ttl
        self.save(
            update_fields=[
                "password_link_token_hash",
                "password_link_purpose",
                "password_link_expires_at",
                "updated_at",
            ]
        )
        return token

    def password_link_is_valid(self, token: str) -> bool:
        """Validate a raw token without leaking timing information."""
        if not token or not self.password_link_token_hash or not self.password_link_expires_at:
            return False
        if self.password_link_expires_at <= timezone.now() or self.deleted_at is not None:
            return False
        return constant_time_compare(
            self.password_link_token_hash,
            self.password_link_hash(token),
        )

    def clear_password_link(self) -> None:
        self.password_link_token_hash = ""
        self.password_link_purpose = ""
        self.password_link_expires_at = None

    def delete(self, using=None, keep_parents=False, hard: bool = False):
        """Soft deleting a user also revokes their ability to log in."""
        if not hard:
            self.is_active = False
            self.deleted_at = timezone.now()
            self.save(update_fields=["is_active", "deleted_at", "updated_at"])
            return (1, {self._meta.label: 1})
        return super().delete(using=using, keep_parents=keep_parents, hard=True)
