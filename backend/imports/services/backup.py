"""Portable ``.fin`` household backup format and full restore."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction as db_transaction
from django.utils import timezone

from base.models import File, Setting, Tag
from finance.models import Account, Category, Contract, Job, Loan, Transaction

FORMAT = "fin-household"
VERSION = 1

MODEL_FIELDS: dict[str, tuple[str, ...]] = {
    "accounts": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "holder",
        "kind", "iban", "bank_name", "currency", "color", "opening_balance",
        "opening_balance_date", "include_in_net_worth", "is_active",
    ),
    "categories": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "slug",
        "kind", "color", "icon", "parent_id", "keywords", "is_system", "monthly_budget",
    ),
    "contracts": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "account_id",
        "category_id", "interval", "interval_count", "day_of_month", "start_date",
        "end_date", "is_active", "provider", "amount", "contract_direction",
        "contract_number", "cancellation_period_days",
    ),
    "loans": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "account_id",
        "category_id", "interval", "interval_count", "day_of_month", "start_date",
        "end_date", "is_active", "lender", "principal", "interest_rate", "instalment",
        "remaining_at_start",
    ),
    "jobs": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "account_id",
        "category_id", "interval", "interval_count", "day_of_month", "start_date",
        "end_date", "is_active", "employer", "gross_amount", "net_amount", "tax_class",
        "part_time_factor",
    ),
    "files": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "original_name",
        "content_type", "size", "purpose", "status", "account_id", "stats",
        "error_message", "processed_at",
    ),
    "transactions": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "account_id",
        "category_id", "amount", "booking_date", "state", "source", "counterparty",
        "purpose", "contract_id", "loan_id", "job_id", "recurrence_key", "import_file_id",
        "external_id", "import_hash", "matched_transaction_id", "is_internal_transfer",
        "transfer_pair_id", "classified_by_ai", "classification_confidence",
        "classification_note", "needs_review",
    ),
    "settings": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "key", "value",
        "value_type", "is_secret", "description",
    ),
    "tags": (
        "id", "name", "notes", "created_at", "updated_at", "deleted_at", "db_table",
        "object_uuid", "color",
    ),
}


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if value is not None and value.__class__.__name__ == "UUID":
        return str(value)
    return value


def _row(obj, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: _json_value(getattr(obj, field)) for field in fields}


def _querysets(household) -> dict[str, Any]:
    return {
        "accounts": Account.all_objects.filter(household=household),
        "categories": Category.all_objects.filter(household=household),
        "contracts": Contract.all_objects.filter(account__household=household),
        "loans": Loan.all_objects.filter(account__household=household),
        "jobs": Job.all_objects.filter(account__household=household),
        "files": File.all_objects.filter(household=household).exclude(
            purpose=File.Purpose.BACKUP_IMPORT
        ),
        "transactions": Transaction.all_objects.filter(account__household=household),
        "settings": Setting.all_objects.filter(household=household),
        "tags": Tag.all_objects.filter(household=household),
    }


def build_backup(household) -> io.BytesIO:
    """Build a versioned ZIP container while retaining original uploaded files."""
    buffer = io.BytesIO()
    data: dict[str, list[dict[str, Any]]] = {}
    querysets = _querysets(household)
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key, queryset in querysets.items():
            data[key] = [_row(obj, MODEL_FIELDS[key]) for obj in queryset]
        for row, file_obj in zip(data["files"], querysets["files"]):
            if not file_obj.file:
                continue
            try:
                with file_obj.file.open("rb") as source:
                    content = source.read()
            except Exception:
                continue
            safe_name = Path(file_obj.original_name or file_obj.file.name).name or "datei"
            archive_path = f"files/{file_obj.pk}/{safe_name}"
            archive.writestr(archive_path, content)
            row["archive_path"] = archive_path

        manifest = {
            "format": FORMAT,
            "version": VERSION,
            "exported_at": timezone.now().isoformat(),
            "household": {"id": str(household.pk), "name": household.name},
            "counts": {key: len(rows) for key, rows in data.items()},
        }
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2))
    buffer.seek(0)
    return buffer


def read_backup(content: bytes) -> tuple[dict[str, Any], dict[str, Any], zipfile.ZipFile]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content), "r")
        manifest = json.loads(archive.read("manifest.json"))
        data = json.loads(archive.read("data.json"))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Die .fin-Datei ist keine gültige Finanz-Sicherung.") from exc
    if manifest.get("format") != FORMAT or manifest.get("version") != VERSION:
        archive.close()
        raise ValueError("Diese Version der .fin-Datei wird nicht unterstützt.")
    for key in MODEL_FIELDS:
        if not isinstance(data.get(key, []), list):
            archive.close()
            raise ValueError("Die .fin-Datei enthält ungültige Daten.")
    return manifest, data, archive


def inspect_backup(content: bytes) -> dict[str, Any]:
    manifest, data, archive = read_backup(content)
    archive.close()
    return {
        "kind": "backup",
        "household_name": manifest.get("household", {}).get("name") or "Haushalt",
        "exported_at": manifest.get("exported_at"),
        "counts": {key: len(data.get(key, [])) for key in MODEL_FIELDS},
    }


def _clean_values(row: dict[str, Any], *, omit: tuple[str, ...] = ()) -> dict[str, Any]:
    values = {key: value for key, value in row.items() if key not in omit}
    for key, value in list(values.items()):
        if key.endswith("_at") and value:
            values[key] = datetime.fromisoformat(value)
        elif key.endswith("_date") and value:
            values[key] = date.fromisoformat(value)
    return values


def _hard_delete_current(household) -> None:
    Transaction.all_objects.filter(account__household=household).hard_delete()
    for model in (Contract, Loan, Job):
        model.all_objects.filter(account__household=household).hard_delete()
    Tag.all_objects.filter(household=household).hard_delete()
    Setting.all_objects.filter(household=household).hard_delete()
    Category.all_objects.filter(household=household).hard_delete()
    Account.all_objects.filter(household=household).hard_delete()
    File.all_objects.filter(household=household).hard_delete()


@db_transaction.atomic
def restore_backup(content: bytes, *, household, user) -> dict[str, int]:
    """Replace every household-owned row; user accounts and memberships stay intact."""
    manifest, data, archive = read_backup(content)
    existing_files = list(File.all_objects.filter(household=household))
    _hard_delete_current(household)
    def delete_old_blobs() -> None:
        for old in existing_files:
            try:
                old.file.delete(save=False)
            except Exception:
                pass

    db_transaction.on_commit(delete_old_blobs)

    household.name = manifest.get("household", {}).get("name") or household.name
    household.save(update_fields=["name", "updated_at"])

    models = {
        "accounts": Account,
        "categories": Category,
        "contracts": Contract,
        "loans": Loan,
        "jobs": Job,
        "settings": Setting,
        "tags": Tag,
    }
    for key in ("accounts", "categories"):
        for row in data[key]:
            values = _clean_values(row, omit=("parent_id",))
            values.update({"household": household, "created_by": user})
            models[key].all_objects.create(**values)
    for row in data["categories"]:
        if row.get("parent_id"):
            Category.all_objects.filter(pk=row["id"]).update(parent_id=row["parent_id"])

    for key in ("contracts", "loans", "jobs"):
        for row in data[key]:
            values = _clean_values(row)
            values["created_by"] = user
            models[key].all_objects.create(**values)

    for row in data["files"]:
        archive_path = row.get("archive_path")
        values = _clean_values(row, omit=("archive_path",))
        values.update({"household": household, "created_by": user, "processed_data": {}})
        file_obj = File(**values)
        if archive_path:
            if archive_path.startswith("/") or ".." in Path(archive_path).parts:
                raise ValueError("Die .fin-Datei enthält einen ungültigen Dateipfad.")
            try:
                file_obj.file.save(
                    Path(archive_path).name,
                    ContentFile(archive.read(archive_path)),
                    save=False,
                )
            except KeyError:
                pass
        file_obj.save(force_insert=True)

    for row in data["transactions"]:
        values = _clean_values(
            row, omit=("matched_transaction_id", "transfer_pair_id")
        )
        values["created_by"] = user
        Transaction.all_objects.create(**values)
    for row in data["transactions"]:
        updates = {
            key: row[key]
            for key in ("matched_transaction_id", "transfer_pair_id")
            if row.get(key)
        }
        if updates:
            Transaction.all_objects.filter(pk=row["id"]).update(**updates)

    for key in ("settings", "tags"):
        for row in data[key]:
            values = _clean_values(row)
            values.update({"household": household, "created_by": user})
            models[key].all_objects.create(**values)
    archive.close()
    return {key: len(data[key]) for key in MODEL_FIELDS}
