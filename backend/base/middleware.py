"""Channels middleware: authenticate WebSockets with the same API token."""

from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_for_token(key: str):
    from django.conf import settings
    from django.utils import timezone
    from rest_framework.authtoken.models import Token

    try:
        token = Token.objects.select_related("user", "user__current_household").get(key=key)
    except Token.DoesNotExist:
        return AnonymousUser()
    ttl = getattr(settings, "AUTH_TOKEN_TTL", None)
    if ttl is not None and token.created < timezone.now() - ttl:
        return AnonymousUser()
    return token.user


class TokenAuthMiddleware(BaseMiddleware):
    """
    Reads the token from `?token=…` or the `Authorization: Token …` header.

    Browsers cannot set headers on a WebSocket handshake, so the query
    parameter is the path the frontend actually uses.
    """

    async def __call__(self, scope, receive, send):
        token_key = ""

        query = parse_qs((scope.get("query_string") or b"").decode())
        if query.get("token"):
            token_key = query["token"][0]

        if not token_key:
            for header, value in scope.get("headers", []):
                if header == b"authorization":
                    raw = value.decode()
                    if raw.lower().startswith("token "):
                        token_key = raw.split(" ", 1)[1].strip()
                    break

        scope["user"] = await _user_for_token(token_key) if token_key else AnonymousUser()
        return await super().__call__(scope, receive, send)
