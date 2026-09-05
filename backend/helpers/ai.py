"""Tiny, failure-safe interface for structured AI assistance."""

from __future__ import annotations

import json
import logging
from typing import Any

from base.models import Setting
from base.settings_registry import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

logger = logging.getLogger(__name__)


def configured(*, household=None) -> bool:
    return bool((Setting.get(OPENAI_API_KEY, "", household=household) or "").strip())


def json_response(
    system: str,
    payload: Any,
    *,
    household=None,
    temperature: float = 0,
) -> dict[str, Any] | None:
    """Return one JSON object, or ``None`` when AI is unavailable or fails."""
    api_key = (Setting.get(OPENAI_API_KEY, "", household=household) or "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI

        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": 60.0, "max_retries": 2}
        base_url = (Setting.get(OPENAI_BASE_URL, "", household=household) or "").strip()
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)
        model = (
            Setting.get(OPENAI_MODEL, "gpt-4.1-mini", household=household)
            or "gpt-4.1-mini"
        ).strip()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:  # AI may improve a workflow, but must never block it.
        logger.warning("KI-Anfrage fehlgeschlagen: %s", exc)
        return None
