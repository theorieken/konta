"""
One place that decides between "run in the background" and "run right now".

Celery is always available in the docker stack, but a broker can be down and
tests run without one. `enqueue` therefore never raises: it tries `.delay()`
and falls back to executing the task inline, so an upload or a form save can
never fail just because the queue is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def enqueue(task, *args: Any, **kwargs: Any) -> bool:
    """
    Returns True when the task was handed to the broker, False when it had to
    run synchronously (or failed – the error is logged, never propagated).
    """
    try:
        task.delay(*args, **kwargs)
        return True
    except Exception as exc:
        logger.warning(
            "Celery nicht erreichbar (%s) – %s wird direkt ausgeführt.",
            exc.__class__.__name__,
            getattr(task, "name", task),
        )

    try:
        task(*args, **kwargs)
    except Exception:
        logger.exception("Aufgabe %s ist fehlgeschlagen.", getattr(task, "name", task))
    return False
