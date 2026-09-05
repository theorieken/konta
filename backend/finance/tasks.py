"""Periodic domain work – wired up in `base/management/commands/setup_periodic_tasks.py`."""

from __future__ import annotations

import logging

from celery import shared_task

from base.events import broadcast_event

logger = logging.getLogger(__name__)


@shared_task(name="finance.generate_planned_transactions")
def generate_planned_transactions(months: int | None = None) -> dict:
    """Materialise Contract/Loan/Job occurrences up to the prediction horizon."""
    from finance.services.generator import generate_all

    result = generate_all(months).as_dict()
    if result["created"]:
        broadcast_event({"type": "plan.generated", **result})
    return result


@shared_task(name="finance.resync_source")
def resync_source(db_table: str, object_uuid: str) -> dict:
    """Rebuild the future plan of a single Contract/Loan/Job after an edit."""
    from base.registry import get_model_for_table
    from finance.services.generator import resync_source as resync

    model = get_model_for_table(db_table)
    source = model.objects.filter(pk=object_uuid).first()
    if source is None:
        return {"removed": 0, "created": 0, "found": False}
    removed, created = resync(source)
    broadcast_event(
        {
            "type": "plan.generated",
            "object_reference": source.object_reference,
            "removed": removed,
            "created": created,
        }
    )
    return {"removed": removed, "created": created, "found": True}


@shared_task(name="finance.match_transactions")
def match_transactions(limit: int = 2000) -> dict:
    """Link booked transactions to the plan they fulfil."""
    from finance.services.matching import match_unmatched

    result = match_unmatched(limit=limit)
    if result["matched"]:
        broadcast_event({"type": "plan.matched", **result})
    return result


@shared_task(name="finance.flag_overdue_planned")
def flag_overdue_planned(grace_days: int = 10) -> int:
    """
    Planned transactions whose date has passed without a matching booking are
    flagged for review so the user notices a forgotten payment.
    """
    from datetime import timedelta

    from django.utils import timezone

    from finance.models import Transaction

    cutoff = timezone.localdate() - timedelta(days=grace_days)
    updated = Transaction.objects.filter(
        state=Transaction.State.PLANNED,
        matched_transaction__isnull=True,
        booking_date__lt=cutoff,
        needs_review=False,
    ).update(needs_review=True)
    if updated:
        logger.info("%s überfällige geplante Transaktionen markiert", updated)
    return updated
