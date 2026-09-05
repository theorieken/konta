"""Token authentication with an optional expiry (AUTH_TOKEN_TTL_DAYS)."""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    `Authorization: Token <key>` – the single auth scheme of this API.

    Tokens expire after `settings.AUTH_TOKEN_TTL` (set `AUTH_TOKEN_TTL_DAYS=0`
    to disable expiry). Expired tokens are deleted so the client gets a clean
    401 and simply logs in again.
    """

    keyword = "Token"

    def authenticate_credentials(self, key: str):
        user, token = super().authenticate_credentials(key)
        ttl = getattr(settings, "AUTH_TOKEN_TTL", None)
        if ttl is not None and token.created < timezone.now() - ttl:
            token.delete()
            raise exceptions.AuthenticationFailed("Token abgelaufen. Bitte neu anmelden.")
        return user, token


def issue_token(user) -> Token:
    """Create a fresh token, replacing an expired one."""
    token, created = Token.objects.get_or_create(user=user)
    ttl = getattr(settings, "AUTH_TOKEN_TTL", None)
    if not created and ttl is not None and token.created < timezone.now() - ttl:
        token.delete()
        token = Token.objects.create(user=user)
    return token
