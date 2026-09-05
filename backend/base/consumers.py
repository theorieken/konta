"""
WebSocket consumer for live updates.

The frontend opens exactly one socket (`/ws/events/?token=…`) and receives
every change as a small envelope:

    {"type": "object.changed", "action": "created|updated|deleted",
     "object_reference": "finance_transaction-…", "db_table": "…",
     "payload": {...}}

    {"type": "import.progress", "object_reference": "base_file-…",
     "status": "processing", "processed": 120, "total": 340}
"""

from __future__ import annotations

import json
from typing import Any

from channels.generic.websocket import AsyncWebsocketConsumer

HOUSEHOLD_GROUP = "household"


def household_group(household_id) -> str:
    return f"{HOUSEHOLD_GROUP}.{household_id}" if household_id else HOUSEHOLD_GROUP


class EventsConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group_names = list(
            dict.fromkeys(
                [HOUSEHOLD_GROUP, household_group(getattr(user, "current_household_id", None))]
            )
        )
        for group_name in self.group_names:
            await self.channel_layer.group_add(group_name, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"type": "connection.ready", "user": str(user.pk)}))

    async def disconnect(self, code: int) -> None:
        for group_name in getattr(self, "group_names", []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        """Only ping/pong – this socket is a one way push channel."""
        if not text_data:
            return
        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if message.get("type") == "ping":
            await self.send(json.dumps({"type": "pong"}))

    # -- group handlers (names match the `type` used by group_send) -----------
    async def broadcast(self, event: dict[str, Any]) -> None:
        await self.send(json.dumps(event.get("payload", {}), default=str))
