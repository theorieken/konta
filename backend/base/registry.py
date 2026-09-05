"""
Object registry: everything addressable by ``{db_table}-{uuid}``.

The registry is what makes the generic `/api/objects/{reference}/` endpoint and
the frontend's `ObjectDrawer` work without a per-model special case.
"""

from __future__ import annotations

import uuid as uuid_lib
from functools import lru_cache
from typing import Iterable, Type

from django.apps import apps
from django.core.exceptions import ValidationError

from base.models import BaseModel

# Apps whose models participate in the generic object API.
REGISTERED_APPS = ("base", "users", "finance", "imports")

UUID_LENGTH = 36  # 8-4-4-4-12


@lru_cache(maxsize=1)
def model_registry() -> dict[str, Type[BaseModel]]:
    """`{db_table: model_class}` for every concrete BaseModel subclass."""
    registry: dict[str, Type[BaseModel]] = {}
    for model in apps.get_models():
        if not issubclass(model, BaseModel):
            continue
        if model._meta.app_label not in REGISTERED_APPS:
            continue
        registry[model._meta.db_table] = model
    return registry


def registered_models() -> Iterable[Type[BaseModel]]:
    return model_registry().values()


def get_model_for_table(db_table: str) -> Type[BaseModel]:
    try:
        return model_registry()[db_table]
    except KeyError as exc:
        raise ValidationError(f"Unbekannte Tabelle: {db_table}") from exc


def split_reference(reference: str) -> tuple[str, str]:
    """
    Split ``finance_transaction-4f0e...`` into ``("finance_transaction", "4f0e...")``.

    Table names may contain underscores and UUIDs contain dashes, so we anchor
    on the fixed 36 character UUID at the end instead of splitting on "-".
    """
    reference = (reference or "").strip()
    if len(reference) < UUID_LENGTH + 2 or reference[-(UUID_LENGTH + 1)] != "-":
        raise ValidationError(f"Ungültige Objektreferenz: {reference}")
    db_table = reference[: -(UUID_LENGTH + 1)]
    raw_uuid = reference[-UUID_LENGTH:]
    try:
        parsed = uuid_lib.UUID(raw_uuid)
    except (ValueError, AttributeError) as exc:
        raise ValidationError(f"Ungültige UUID in Referenz: {reference}") from exc
    return db_table, str(parsed)


def build_reference(obj: BaseModel) -> str:
    return f"{obj._meta.db_table}-{obj.pk}"


def resolve_reference(reference: str, *, include_deleted: bool = False) -> BaseModel:
    """Return the object a reference points to, or raise ValidationError/DoesNotExist."""
    db_table, object_uuid = split_reference(reference)
    model = get_model_for_table(db_table)
    manager = model.all_objects if include_deleted else model.objects
    return manager.get(pk=object_uuid)


def resolve_reference_or_none(reference: str, *, include_deleted: bool = False):
    try:
        return resolve_reference(reference, include_deleted=include_deleted)
    except (ValidationError, LookupError, Exception):
        return None


def serializer_for(obj: BaseModel):
    """Look up the canonical serializer class for a model instance."""
    from base.serializers import SERIALIZER_REGISTRY

    return SERIALIZER_REGISTRY.get(obj._meta.db_table)
