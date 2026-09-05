"""
Helpers for pushing changes to connected clients.

Every mutation that the UI should react to goes through `broadcast_object` or
`broadcast_event`. Both are safe to call from Celery workers and from request
handlers, and they never raise – a missing channel layer must not break a
write.
"""

from __future__ import annotations

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from base.consumers import HOUSEHOLD_GROUP, household_group

logger = logging.getLogger(__name__)


def broadcast_event(
    payload: dict[str, Any],
    group: str | None = None,
    *,
    household=None,
) -> None:
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        target = group or household_group(getattr(household, "pk", household))
        async_to_sync(layer.group_send)(target, {"type": "broadcast", "payload": payload})
    except Exception:  # pragma: no cover - never break the caller
        logger.warning("WebSocket-Broadcast fehlgeschlagen", exc_info=True)


def broadcast_object(obj, action: str, payload: dict[str, Any] | None = None) -> None:
    """action is one of created / updated / deleted."""
    from base.households import object_household
    from base.models import Household

    household = obj if isinstance(obj, Household) else object_household(obj)
    broadcast_event(
        {
            "type": "object.changed",
            "action": action,
            "object_reference": obj.object_reference,
            "db_table": obj._meta.db_table,
            "name": obj.display_name,
            "payload": payload or {},
        },
        household=household,
    )


def broadcast_import_progress(file_obj, processed: int, total: int, message: str = "") -> None:
    broadcast_event(
        {
            "type": "import.progress",
            "object_reference": file_obj.object_reference,
            "status": file_obj.status,
            "processed": processed,
            "total": total,
            "message": message,
        },
        household=file_obj.household,
    )


def broadcast_toast(message: str, severity: str = "info") -> None:
    broadcast_event({"type": "toast", "severity": severity, "message": message})
