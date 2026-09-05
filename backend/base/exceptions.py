"""Uniform error envelope so the frontend can show one toast component."""

from __future__ import annotations

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _readable(value) -> str:
    """Turn DRF ErrorDetail containers into a clean user-facing sentence."""
    if isinstance(value, dict):
        return "; ".join(_readable(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return "; ".join(_readable(item) for item in value)
    return str(value)


def api_exception_handler(exc, context) -> Response | None:
    if isinstance(exc, DjangoValidationError):
        return Response(
            {"detail": "; ".join(exc.messages), "errors": {}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, ObjectDoesNotExist):
        return Response({"detail": "Objekt nicht gefunden.", "errors": {}},
                        status=status.HTTP_404_NOT_FOUND)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unbehandelter Fehler in %s", context.get("view"))
        return Response(
            {"detail": "Interner Serverfehler.", "errors": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        response.data = {"detail": _readable(data["detail"]), "errors": {}}
    elif isinstance(data, dict):
        response.data = {
            "detail": "Die Eingaben sind unvollständig oder ungültig.",
            "errors": data,
        }
    elif isinstance(data, list):
        response.data = {"detail": _readable(data), "errors": {}}
    return response
