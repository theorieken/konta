"""Two-phase imports: analyse safely, then commit after explicit confirmation."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import IntegrityError, transaction as db_transaction
from django.utils import timezone

from base.events import broadcast_event, broadcast_import_progress, broadcast_object
from base.models import File
from base.queue import enqueue
from finance.models import Category, Transaction
from finance.services.seed import get_fallback_category

logger = logging.getLogger(__name__)


def _read_file(file_obj: File) -> bytes:
    with file_obj.file.open("rb") as handle:
        return handle.read()


def _fail(file_obj: File, message: str) -> dict:
    file_obj.mark(File.Status.FAILED, error=message)
    broadcast_object(file_obj, "updated")
    return {"error": message, "file": str(file_obj.pk)}


def _find_internal_pair(
    row: dict,
    *,
    account,
    household,
    existing: list[Transaction] | None = None,
) -> Transaction | None:
    """Find the opposite leg of a transfer already imported on another account."""
    booking_date = date.fromisoformat(row["booking_date"])
    amount = -Decimal(str(row["amount"]))
    candidates = existing
    if candidates is None:
        candidates = list(
            Transaction.objects.filter(
                account__household=household,
                state=Transaction.State.REALITY,
                transfer_pair__isnull=True,
            )
            .exclude(account=account)
            .select_related("account")
        )
    candidates = [
        tx
        for tx in candidates
        if tx.amount == amount
        and booking_date - timedelta(days=2) <= tx.booking_date <= booking_date + timedelta(days=2)
    ]
    return min(
        candidates,
        key=lambda tx: abs((tx.booking_date - booking_date).days),
        default=None,
    )


def _analyse_csv(file_obj: File, content: bytes) -> dict:
    from imports.services.classifier import batch_size, classify_candidates
    from imports.services.csv_parser import parse_rows

    account = file_obj.account
    if account is None or account.household_id != file_obj.household_id:
        raise ValueError("Für den CSV-Import muss ein Konto des aktiven Haushalts gewählt werden.")

    rows, report = parse_rows(content)
    known_hashes = set(
        Transaction.all_objects.filter(account=account)
        .exclude(import_hash="")
        .values_list("import_hash", flat=True)
    )
    candidates: list[dict] = []
    duplicates = 0
    for index, parsed in enumerate(rows):
        fingerprint = parsed.fingerprint(str(account.pk))
        if fingerprint in known_hashes:
            duplicates += 1
            continue
        known_hashes.add(fingerprint)
        candidates.append(
            {
                "index": index,
                "name": parsed.describe()[:255],
                "booking_date": parsed.booking_date.isoformat(),
                "amount": str(parsed.amount),
                "counterparty": parsed.counterparty[:255],
                "purpose": parsed.purpose,
                "external_id": parsed.external_id[:200],
                "import_hash": fingerprint,
            }
        )

    transfer_category = Category.objects.filter(
        household=file_obj.household, slug="umbuchung"
    ).first()
    candidate_dates = [date.fromisoformat(row["booking_date"]) for row in candidates]
    opposite_amounts = [-Decimal(str(row["amount"])) for row in candidates]
    transfer_pool = []
    if candidate_dates:
        transfer_pool = list(
            Transaction.objects.filter(
                account__household=file_obj.household,
                state=Transaction.State.REALITY,
                transfer_pair__isnull=True,
                booking_date__gte=min(candidate_dates) - timedelta(days=2),
                booking_date__lte=max(candidate_dates) + timedelta(days=2),
                amount__in=opposite_amounts,
            )
            .exclude(account=account)
            .select_related("account")
        )
    internal = 0
    for row in candidates:
        pair = _find_internal_pair(
            row,
            account=account,
            household=file_obj.household,
            existing=transfer_pool,
        )
        if pair is None:
            row["is_internal_transfer"] = False
            row["transfer_pair"] = None
            continue
        transfer_pool.remove(pair)
        internal += 1
        row["is_internal_transfer"] = True
        row["transfer_pair"] = str(pair.pk)
        row["transfer_pair_name"] = f"{pair.account.name} · {pair.booking_date:%d.%m.%Y}"

    classifiable = [row for row in candidates if not row["is_internal_transfer"]]
    ai_used = False
    size = batch_size(household=file_obj.household)
    for offset in range(0, len(classifiable), size):
        batch = classifiable[offset:offset + size]
        ai_used = classify_candidates(batch, household=file_obj.household) or ai_used
        broadcast_import_progress(
            file_obj,
            min(offset + len(batch), len(classifiable)),
            len(classifiable),
            "Buchungen werden intelligent aufbereitet",
        )

    for row in classifiable:
        if row.get("category_slug") == "umbuchung":
            row["is_internal_transfer"] = True
            row["needs_review"] = False
            row["classification_note"] = "Interne Umbuchung erkannt"
            internal += 1

    for row in candidates:
        if not row["is_internal_transfer"]:
            continue
        row["needs_review"] = False
        row["classification_confidence"] = 1.0
        row["classification_note"] = "Interne Gegenbuchung erkannt"
        if transfer_category is not None:
            row["category"] = str(transfer_category.pk)
            row["category_name"] = transfer_category.name
            row["category_slug"] = transfer_category.slug

    dates = [row["booking_date"] for row in candidates]
    stats = {
        **report,
        "kind": "transactions",
        "stage": "ready",
        "total": len(rows),
        "new": len(candidates),
        "duplicates": duplicates,
        "internal_transfers": internal,
        "needs_review": sum(bool(row.get("needs_review")) for row in candidates),
        "ai_used": ai_used,
        "date_from": min(dates) if dates else None,
        "date_until": max(dates) if dates else None,
    }
    file_obj.processed_data = {"rows": candidates}
    file_obj.save(update_fields=["processed_data", "updated_at"])
    file_obj.mark(File.Status.READY, stats=stats)
    broadcast_object(file_obj, "updated")
    broadcast_event(
        {"type": "import.analyzed", "object_reference": file_obj.object_reference, **stats},
        household=file_obj.household,
    )
    return stats


@shared_task(name="imports.analyse_import_file", bind=True, max_retries=1)
def analyse_import_file(self, file_id: str) -> dict:
    """Parse, deduplicate, classify and pair transfers without changing balances."""
    from imports.services.backup import inspect_backup
    from imports.services.csv_parser import CsvParseError

    file_obj = File.objects.select_related("account", "household").filter(pk=file_id).first()
    if file_obj is None:
        return {"error": "Datei nicht gefunden", "file": file_id}
    file_obj.mark(File.Status.PROCESSING, stats={"stage": "analysing"})
    broadcast_object(file_obj, "updated")
    try:
        content = _read_file(file_obj)
        if file_obj.purpose == File.Purpose.BACKUP_IMPORT or file_obj.original_name.lower().endswith(".fin"):
            file_obj.purpose = File.Purpose.BACKUP_IMPORT
            stats = {**inspect_backup(content), "stage": "ready"}
            file_obj.save(update_fields=["purpose", "updated_at"])
            file_obj.mark(File.Status.READY, stats=stats)
            broadcast_object(file_obj, "updated")
            broadcast_event(
                {"type": "import.analyzed", "object_reference": file_obj.object_reference, **stats},
                household=file_obj.household,
            )
            return stats
        return _analyse_csv(file_obj, content)
    except (CsvParseError, ValueError) as exc:
        return _fail(file_obj, str(exc))
    except Exception as exc:
        logger.exception("Importanalyse fehlgeschlagen für %s", file_id)
        return _fail(file_obj, f"Datei konnte nicht verarbeitet werden: {exc}")


@shared_task(name="imports.import_transactions_from_file")
def import_transactions_from_file(file_id: str) -> dict:
    """Compatibility route for workers that still know the previous task name."""
    return analyse_import_file.run(file_id)


@shared_task(name="imports.commit_import", bind=True, max_retries=1)
def commit_import(self, file_id: str, user_id: str, restore: bool = False) -> dict:
    """Apply a reviewed transaction import or a confirmed full restore."""
    from users.models import User

    file_obj = File.objects.select_related("account", "household").filter(pk=file_id).first()
    user = User.objects.filter(pk=user_id).first()
    if file_obj is None or user is None:
        return {"error": "Import oder Benutzer nicht gefunden"}
    if file_obj.status not in (File.Status.READY, File.Status.PROCESSING) or (
        file_obj.status == File.Status.PROCESSING
        and file_obj.stats.get("stage") != "queued"
    ):
        return _fail(file_obj, "Dieser Import ist nicht zur Übernahme bereit.")

    if file_obj.purpose == File.Purpose.BACKUP_IMPORT:
        if not restore:
            return _fail(file_obj, "Die vollständige Wiederherstellung wurde nicht bestätigt.")
        from imports.services.backup import restore_backup

        content = _read_file(file_obj)
        file_obj.mark(File.Status.PROCESSING, stats={**file_obj.stats, "stage": "restoring"})
        try:
            counts = restore_backup(content, household=file_obj.household, user=user)
        except Exception as exc:
            logger.exception("Wiederherstellung fehlgeschlagen")
            current = File.objects.filter(pk=file_id).first()
            if current:
                _fail(current, f"Wiederherstellung fehlgeschlagen: {exc}")
            return {"error": str(exc)}
        broadcast_event(
            {"type": "household.restored", "counts": counts},
            household=file_obj.household,
        )
        return {"restored": counts}

    account = file_obj.account
    if account is None:
        return _fail(file_obj, "Dem Import ist kein Konto zugeordnet.")
    file_obj.mark(File.Status.PROCESSING, stats={**file_obj.stats, "stage": "importing"})
    fallback = get_fallback_category(household=file_obj.household)
    created: list[Transaction] = []
    duplicates = int(file_obj.stats.get("duplicates", 0))
    matched = 0

    for row in file_obj.processed_data.get("rows", []):
        category = Category.objects.filter(
            pk=row.get("category"), household=file_obj.household
        ).first() or fallback
        try:
            with db_transaction.atomic():
                tx = Transaction.objects.create(
                    name=row.get("name", "")[:255],
                    account=account,
                    category=category,
                    amount=Decimal(str(row["amount"])),
                    booking_date=date.fromisoformat(row["booking_date"]),
                    state=Transaction.State.REALITY,
                    source=Transaction.Source.IMPORT,
                    counterparty=row.get("counterparty", "")[:255],
                    purpose=row.get("purpose", ""),
                    external_id=row.get("external_id", "")[:200],
                    import_hash=row["import_hash"],
                    import_file=file_obj,
                    is_internal_transfer=bool(row.get("is_internal_transfer")),
                    transfer_pair_id=row.get("transfer_pair"),
                    classified_by_ai=bool(row.get("classified_by_ai")),
                    classification_confidence=row.get("classification_confidence"),
                    classification_note=row.get("classification_note", "")[:500],
                    needs_review=bool(row.get("needs_review")),
                    created_by=user,
                )
        except IntegrityError:
            duplicates += 1
            continue
        created.append(tx)
        if tx.transfer_pair_id:
            pair = Transaction.objects.filter(
                pk=tx.transfer_pair_id, account__household=file_obj.household
            ).first()
            if pair is not None:
                transfer_category = Category.objects.filter(
                    household=file_obj.household, slug="umbuchung"
                ).first()
                updates = {"is_internal_transfer": True, "transfer_pair": tx}
                if transfer_category is not None:
                    updates["category"] = transfer_category
                Transaction.objects.filter(pk=pair.pk).update(**updates)

    from finance.services.matching import match_transaction

    for tx in created:
        if not tx.is_internal_transfer and match_transaction(tx) is not None:
            matched += 1
    stats = {
        **file_obj.stats,
        "stage": "done",
        "imported": len(created),
        "duplicates": duplicates,
        "matched": matched,
    }
    file_obj.mark(File.Status.COMPLETED, stats=stats)
    broadcast_object(file_obj, "updated")
    broadcast_event(
        {
            "type": "import.finished",
            "object_reference": file_obj.object_reference,
            "imported": len(created),
            "duplicates": duplicates,
            "matched": matched,
        },
        household=file_obj.household,
    )
    return stats


@shared_task(name="imports.classify_transactions")
def classify_transactions(
    transaction_ids: list[str],
    file_id: str | None = None,
    batch_number: int = 1,
    batch_total: int = 1,
) -> dict:
    """Reclassify existing rows; retained for the review action."""
    from finance.services.matching import match_transaction
    from imports.services.classifier import classify_batch

    transactions = list(
        Transaction.objects.filter(pk__in=transaction_ids).select_related(
            "account", "category", "account__household"
        )
    )
    result = classify_batch(transactions)
    matched = sum(
        1
        for tx in transactions
        if tx.matched_transaction_id is None and match_transaction(tx) is not None
    )
    return {**result.as_dict(), "matched": matched, "batch": batch_number}


@shared_task(name="imports.reclassify_transactions")
def reclassify_transactions(
    transaction_ids: list[str] | None = None,
    only_review: bool = True,
    household_id: str | None = None,
) -> dict:
    from imports.services.classifier import batch_size
    from imports.services.csv_parser import chunked

    queryset = Transaction.objects.all()
    if household_id:
        queryset = queryset.filter(account__household_id=household_id)
    if transaction_ids:
        queryset = queryset.filter(pk__in=transaction_ids)
    elif only_review:
        queryset = queryset.filter(needs_review=True, state=Transaction.State.REALITY)
    ids = [str(pk) for pk in queryset.values_list("pk", flat=True)[:5000]]
    first = queryset.select_related("account__household").first() if ids else None
    batches = list(chunked(ids, batch_size(household=first.account.household if first else None)))
    for position, batch in enumerate(batches):
        enqueue(classify_transactions, batch, None, position + 1, len(batches))
    return {"queued": len(ids), "batches": len(batches)}


@shared_task(name="imports.cleanup_stale_imports")
def cleanup_stale_imports(hours: int = 6) -> int:
    cutoff = timezone.now() - timedelta(hours=hours)
    stale = File.objects.filter(
        purpose__in=[File.Purpose.TRANSACTION_IMPORT, File.Purpose.BACKUP_IMPORT],
        status=File.Status.PROCESSING,
        updated_at__lt=cutoff,
    )
    count = 0
    for file_obj in stale:
        file_obj.mark(File.Status.FAILED, error="Import wurde abgebrochen (Zeitüberschreitung).")
        broadcast_object(file_obj, "updated")
        count += 1
    return count
