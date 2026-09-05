"""Housekeeping tasks that are not tied to a single domain app."""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="base.purge_soft_deleted")
def purge_soft_deleted(days: int = 90) -> dict[str, int]:
    """Permanently remove objects that have been in the bin for `days`."""
    from base.registry import registered_models

    cutoff = timezone.now() - timedelta(days=days)
    removed: dict[str, int] = {}
    for model in registered_models():
        queryset = model.all_objects.filter(deleted_at__lt=cutoff)
        count = queryset.count()
        if count:
            queryset.hard_delete()
            removed[model._meta.db_table] = count
    if removed:
        logger.info("Endgültig gelöscht: %s", removed)
    return removed


@shared_task(name="base.prune_expired_tokens")
def prune_expired_tokens() -> int:
    """Delete auth tokens that are past their TTL."""
    from django.conf import settings
    from rest_framework.authtoken.models import Token

    ttl = getattr(settings, "AUTH_TOKEN_TTL", None)
    if ttl is None:
        return 0
    deleted, _ = Token.objects.filter(created__lt=timezone.now() - ttl).delete()
    return deleted
