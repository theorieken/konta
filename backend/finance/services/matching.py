"""
Match imported "reality" transactions against previously planned ones.

A planned transaction that has been matched is kept for the audit trail but
excluded from the projection (`Transaction.counts_towards_projection`), so a
rent payment never shows up twice.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q

from base.models import Setting
from base.settings_registry import MATCH_TOLERANCE_DAYS, MATCH_TOLERANCE_PERCENT
from finance.models import Transaction

logger = logging.getLogger(__name__)


def _tolerances(*, household=None) -> tuple[int, Decimal]:
    days = int(Setting.get(MATCH_TOLERANCE_DAYS, 7, household=household) or 7)
    percent = Decimal(
        str(Setting.get(MATCH_TOLERANCE_PERCENT, 15, household=household) or 15)
    )
    return days, percent


def find_match(actual: Transaction) -> Transaction | None:
    """
    Best planned counterpart for a booked transaction.

    Candidates must share the account, the sign of the amount, sit within the
    date tolerance and stay inside the percentage tolerance of the amount.
    The candidate closest in amount (then in date) wins.
    """
    if actual.state != Transaction.State.REALITY or actual.is_internal_transfer:
        return None

    days, percent = _tolerances(household=actual.account.household)
    amount = actual.amount or Decimal("0")
    magnitude = abs(amount)
    delta = (magnitude * percent / Decimal("100")).quantize(Decimal("0.01"))
    # Small amounts need an absolute floor, otherwise nothing ever matches.
    delta = max(delta, Decimal("1.00"))

    sign_filter = Q(amount__lt=0) if amount < 0 else Q(amount__gte=0)

    candidates = (
        Transaction.objects.filter(
            sign_filter,
            account=actual.account,
            state=Transaction.State.PLANNED,
            matched_transaction__isnull=True,
            booking_date__gte=actual.booking_date - timedelta(days=days),
            booking_date__lte=actual.booking_date + timedelta(days=days),
        )
        .exclude(pk=actual.pk)
        .select_related("category")
    )

    best: Transaction | None = None
    best_score: tuple[Decimal, int] | None = None
    for candidate in candidates:
        difference = abs(abs(candidate.amount) - magnitude)
        if difference > delta:
            continue
        date_distance = abs((candidate.booking_date - actual.booking_date).days)
        score = (difference, date_distance)
        if best_score is None or score < best_score:
            best, best_score = candidate, score
    return best


def apply_match(actual: Transaction, planned: Transaction) -> None:
    """Link both directions and inherit the plan's category when it is better."""
    planned.matched_transaction = actual
    planned.save(update_fields=["matched_transaction", "updated_at"])

    updates = ["matched_transaction", "updated_at"]
    actual.matched_transaction = planned
    # A generated plan knows its category from its contract, so it beats any
    # automatic guess – but never a category the user set by hand.
    if planned.source == Transaction.Source.GENERATED and actual.is_auto_categorised:
        actual.category = planned.category
        actual.classification_note = "Aus Plan übernommen"
        actual.classification_confidence = 1.0
        actual.needs_review = False
        updates += ["category", "classification_note", "classification_confidence",
                    "needs_review"]
    for field in ("contract", "loan", "job"):
        if getattr(planned, f"{field}_id") and not getattr(actual, f"{field}_id"):
            setattr(actual, f"{field}_id", getattr(planned, f"{field}_id"))
            updates.append(field)
    actual.save(update_fields=list(dict.fromkeys(updates)))


def match_transaction(actual: Transaction) -> Transaction | None:
    planned = find_match(actual)
    if planned is not None:
        apply_match(actual, planned)
    return planned


def match_unmatched(limit: int = 2000, *, household=None) -> dict[str, int]:
    """Periodic sweep over booked transactions that have no plan attached yet."""
    filters = {
        "state": Transaction.State.REALITY,
        "matched_transaction__isnull": True,
        "is_internal_transfer": False,
    }
    if household is not None:
        filters["account__household"] = household
    queryset = (
        Transaction.objects.filter(
            **filters
        )
        .select_related("account", "category")
        .order_by("-booking_date")[:limit]
    )
    matched = 0
    checked = 0
    for actual in queryset:
        checked += 1
        if match_transaction(actual) is not None:
            matched += 1
    logger.info("Abgleich: %s von %s Buchungen zugeordnet", matched, checked)
    return {"checked": checked, "matched": matched}
