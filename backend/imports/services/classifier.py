"""
Transaction classification.

Primary path: the OpenAI SDK with the model selected in the settings. Every
request handles a batch of transactions (default 25) so a 2.000 row import
costs 80 requests instead of 2.000.

Fallback path: keyword matching against `Category.keywords`. It runs whenever
no API key is configured or the API call fails, which is what keeps a fresh
`bash deploy.sh` installation fully functional without any credentials.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Sequence

from base.models import Setting
from base.settings_registry import OPENAI_BATCH_SIZE
from finance.models import Category, Transaction
from finance.services.seed import get_fallback_category
from helpers.ai import json_response
from imports.services.csv_parser import normalise

logger = logging.getLogger(__name__)

LOW_CONFIDENCE = 0.6

SYSTEM_PROMPT = """Du bist ein Buchhaltungsassistent für einen privaten Haushalt in Deutschland.
Du ordnest Kontoumsätze genau einer Kategorie aus einer vorgegebenen Liste zu.

Regeln:
- Verwende ausschließlich die vorgegebenen Kategorie-Slugs.
- Negative Beträge sind Ausgaben, positive Beträge sind Einnahmen.
  Wähle für Ausgaben keine reine Einnahmen-Kategorie und umgekehrt.
- Wenn du unsicher bist, wähle "sonstiges" und gib eine niedrige Konfidenz an.
- Antworte ausschließlich mit JSON, ohne Fließtext und ohne Markdown.

Antwortformat:
{"results": [{"index": 0, "category": "haushalt", "confidence": 0.93, "reason": "REWE Supermarkt"}]}
Die Begründung ist maximal 8 Wörter lang und auf Deutsch."""


@dataclass
class ClassificationResult:
    classified: int = 0
    ai_used: bool = False
    fallback: int = 0
    errors: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "classified": self.classified,
            "ai_used": self.ai_used,
            "fallback": self.fallback,
            "errors": self.errors or [],
        }


def batch_size(*, household=None) -> int:
    try:
        return max(
            1,
            min(
                int(Setting.get(OPENAI_BATCH_SIZE, 25, household=household) or 25),
                100,
            ),
        )
    except (TypeError, ValueError):
        return 25


def category_catalogue(*, household=None) -> list[dict[str, Any]]:
    return [
        {
            "slug": category.slug,
            "name": category.name,
            "kind": category.kind,
            "keywords": (category.keywords or [])[:12],
        }
        for category in Category.objects.filter(household=household).order_by("kind", "name")
    ]


def transaction_payload(transactions: Sequence[Transaction]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "date": tx.booking_date.isoformat(),
            "amount": float(tx.amount),
            "counterparty": (tx.counterparty or "")[:120],
            "purpose": (tx.purpose or "")[:240],
        }
        for index, tx in enumerate(transactions)
    ]


# -----------------------------------------------------------------------------
# Keyword fallback
# -----------------------------------------------------------------------------
def classify_by_keywords(tx, categories: list[Category], *, household=None) -> tuple[Category, float, str]:
    haystack = normalise(f"{tx.counterparty} {tx.purpose} {tx.name}")
    is_income = (tx.amount or 0) >= 0

    best: tuple[Category, float, str] | None = None
    for category in categories:
        if is_income and category.kind == Category.Kind.EXPENSE:
            continue
        if not is_income and category.kind == Category.Kind.INCOME:
            continue
        for keyword in category.keywords or []:
            needle = normalise(keyword)
            if needle and needle in haystack:
                score = 0.5 + min(len(needle) / 40, 0.35)
                if best is None or score > best[1]:
                    best = (category, score, f"Stichwort „{keyword}“")
    if best is not None:
        return best

    fallback = get_fallback_category(household=household)
    return fallback, 0.2, "Keine Zuordnung gefunden"


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------
def classify_batch(transactions: Sequence[Transaction]) -> ClassificationResult:
    """Classify one batch in place. Never raises – falls back to keywords."""
    result = ClassificationResult(errors=[])
    transactions = [tx for tx in transactions if tx is not None]
    if not transactions:
        return result

    household = transactions[0].account.household
    categories = list(Category.objects.filter(household=household))
    by_slug = {category.slug: category for category in categories}

    assignments: dict[int, tuple[Category, float, str, bool]] = {}
    payload = json_response(
        SYSTEM_PROMPT,
        {
            "categories": category_catalogue(household=household),
            "transactions": transaction_payload(transactions),
        },
        household=household,
    )

    if payload is not None:
        try:
            for entry in payload.get("results", []):
                try:
                    index = int(entry["index"])
                except (KeyError, TypeError, ValueError):
                    continue
                category = by_slug.get(str(entry.get("category", "")).strip())
                if category is None or not 0 <= index < len(transactions):
                    continue
                confidence = float(entry.get("confidence") or 0.0)
                reason = str(entry.get("reason") or "")[:200]
                assignments[index] = (category, confidence, reason, True)
            result.ai_used = bool(assignments)
        except Exception as exc:
            logger.warning("KI-Kategorisierung fehlgeschlagen: %s", exc)
            result.errors.append(str(exc)[:300])

    # Everything the model did not answer for gets the keyword treatment.
    for index, tx in enumerate(transactions):
        if index in assignments:
            continue
        category, confidence, reason = classify_by_keywords(
            tx, categories, household=household
        )
        assignments[index] = (category, confidence, reason, False)
        result.fallback += 1

    for index, (category, confidence, reason, by_ai) in assignments.items():
        tx = transactions[index]
        tx.category = category
        tx.classified_by_ai = by_ai
        tx.classification_confidence = round(confidence, 3)
        tx.classification_note = reason
        tx.needs_review = confidence < LOW_CONFIDENCE
        tx.save(
            update_fields=[
                "category",
                "classified_by_ai",
                "classification_confidence",
                "classification_note",
                "needs_review",
                "updated_at",
            ]
        )
        result.classified += 1

    return result


def classify_candidates(rows: list[dict[str, Any]], *, household) -> bool:
    """Add category suggestions to parsed rows without creating transactions."""
    from types import SimpleNamespace

    categories = list(Category.objects.filter(household=household))
    by_slug = {category.slug: category for category in categories}
    payload = json_response(
        SYSTEM_PROMPT,
        {
            "categories": category_catalogue(household=household),
            "transactions": [
                {
                    "index": index,
                    "date": row["booking_date"],
                    "amount": float(row["amount"]),
                    "counterparty": row.get("counterparty", "")[:120],
                    "purpose": row.get("purpose", "")[:240],
                }
                for index, row in enumerate(rows)
            ],
        },
        household=household,
    )
    assignments: dict[int, tuple[Category, float, str, bool]] = {}
    for entry in (payload or {}).get("results", []):
        try:
            index = int(entry["index"])
            category = by_slug.get(str(entry.get("category", "")).strip())
            if category is None or not 0 <= index < len(rows):
                continue
            assignments[index] = (
                category,
                float(entry.get("confidence") or 0),
                str(entry.get("reason") or "")[:200],
                True,
            )
        except (KeyError, TypeError, ValueError):
            continue

    for index, row in enumerate(rows):
        if index in assignments:
            category, confidence, reason, by_ai = assignments[index]
        else:
            candidate = SimpleNamespace(
                counterparty=row.get("counterparty", ""),
                purpose=row.get("purpose", ""),
                name=row.get("name", ""),
                amount=Decimal(str(row["amount"])),
            )
            category, confidence, reason = classify_by_keywords(
                candidate, categories, household=household
            )
            by_ai = False
        row.update(
            {
                "category": str(category.pk),
                "category_name": category.name,
                "category_slug": category.slug,
                "classification_confidence": round(confidence, 3),
                "classification_note": reason,
                "classified_by_ai": by_ai,
                "needs_review": confidence < LOW_CONFIDENCE,
            }
        )
    return bool(payload)
