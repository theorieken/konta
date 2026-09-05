"""
Materialise planned transactions from Contracts, Loans and Jobs.

Run by celery beat (`finance.generate_planned_transactions`) and whenever a
source is created or changed. The `recurrence_key` on every generated row
makes the whole operation idempotent – running it twice changes nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from dateutil.relativedelta import relativedelta
from django.db import transaction as db_transaction
from django.utils import timezone

from base.models import Setting
from base.settings_registry import PREDICTION_HORIZON_MONTHS
from finance.models import Contract, Job, Loan, Transaction

logger = logging.getLogger(__name__)

SOURCE_FIELDS = {Contract: "contract", Loan: "loan", Job: "job"}


@dataclass
class GenerationResult:
    created: int = 0
    removed: int = 0
    sources: int = 0
    horizon: date | None = None
    details: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "created": self.created,
            "removed": self.removed,
            "sources": self.sources,
            "horizon": self.horizon.isoformat() if self.horizon else None,
            "details": self.details,
        }


def horizon_date(months: int | None = None, *, household=None) -> date:
    if months is None:
        months = int(
            Setting.get(PREDICTION_HORIZON_MONTHS, 24, household=household) or 24
        )
    today = timezone.localdate()
    end = today + relativedelta(months=months)
    # Always plan whole months.
    return date(end.year, end.month, 1) + relativedelta(months=1, days=-1)


def generation_start() -> date:
    """Planned rows start at the beginning of the current month."""
    today = timezone.localdate()
    return date(today.year, today.month, 1)


def _transaction_name(source, due: date) -> str:
    return source.display_name


@db_transaction.atomic
def generate_for_source(source, until: date | None = None, since: date | None = None) -> int:
    """Create the missing planned transactions for one source."""
    until = until or horizon_date(household=source.account.household)
    since = since or generation_start()
    field_name = SOURCE_FIELDS[type(source)]

    existing = set(
        Transaction.all_objects.filter(recurrence_key__startswith=f"{source._meta.db_table}:{source.pk}:")
        .values_list("recurrence_key", flat=True)
    )

    created = 0
    for due in source.occurrences(until=until, since=since):
        key = source.recurrence_key(due)
        if key in existing:
            continue
        Transaction.objects.create(
            name=_transaction_name(source, due),
            account=source.account,
            category=source.category,
            amount=source.signed_amount,
            booking_date=due,
            state=Transaction.State.PLANNED,
            source=Transaction.Source.GENERATED,
            counterparty=getattr(source, "provider", "")
            or getattr(source, "employer", "")
            or getattr(source, "lender", ""),
            recurrence_key=key,
            created_by=source.created_by,
            **{field_name: source},
        )
        created += 1
    return created


@db_transaction.atomic
def clear_future_planned(source, from_date: date | None = None) -> int:
    """
    Drop generated, still unmatched planned rows so they can be rebuilt.

    Matched rows and anything a user touched manually are never removed.
    """
    from_date = from_date or generation_start()
    field_name = SOURCE_FIELDS[type(source)]
    queryset = Transaction.objects.filter(
        **{field_name: source},
        state=Transaction.State.PLANNED,
        source=Transaction.Source.GENERATED,
        matched_transaction__isnull=True,
        booking_date__gte=from_date,
    )
    count = queryset.count()
    queryset.hard_delete()
    return count


def resync_source(source) -> tuple[int, int]:
    """Rebuild every future planned row of one source. Returns (removed, created)."""
    removed = clear_future_planned(source)
    created = generate_for_source(source)
    return removed, created


def generate_all(months: int | None = None, *, household=None) -> GenerationResult:
    """Entry point for celery beat."""
    if household is None:
        from base.models import Household

        combined = GenerationResult()
        for current in Household.objects.all():
            result = generate_all(months, household=current)
            combined.created += result.created
            combined.removed += result.removed
            combined.sources += result.sources
            combined.details.update(result.details)
            if result.horizon and (combined.horizon is None or result.horizon > combined.horizon):
                combined.horizon = result.horizon
        return combined
    until = horizon_date(months, household=household)
    since = generation_start()
    result = GenerationResult(horizon=until)

    for model in (Contract, Loan, Job):
        sources = model.objects.filter(is_active=True).select_related("account", "category")
        if household is not None:
            sources = sources.filter(account__household=household)
        for source in sources:
            created = generate_for_source(source, until=until, since=since)
            result.created += created
            result.sources += 1
            if created:
                result.details[source.object_reference] = created

    logger.info(
        "Geplante Transaktionen erzeugt: %s aus %s Quellen bis %s",
        result.created, result.sources, until,
    )
    return result
