"""
Dashboard projection.

Everything the dashboard shows comes from this one function so the numbers can
never drift apart: the monthly series, the KPI tiles, the category breakdown
and the account balances all use the same definition of "counted transaction".

Counted = every booked transaction + every planned transaction that has not
been matched by a real booking yet.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Q, Sum
from django.utils import timezone

from base.models import Setting
from base.settings_registry import (
    CURRENCY,
    PREDICTION_HORIZON_MONTHS,
    SAVINGS_GOAL,
    SAVINGS_GOAL_DATE,
)
from finance.models import Account, Category, Transaction

ZERO = Decimal("0.00")

MONTH_LABELS = [
    "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


def counted_transactions(*, household=None):
    """
    Booked rows plus planned rows that have not been matched away.

    `TransactionViewSet.get_queryset` applies the same rule, so the list, its
    summary and the dashboard can never disagree about a number.
    """
    queryset = Transaction.objects.exclude(
        Q(state=Transaction.State.PLANNED) & Q(matched_transaction__isnull=False)
    )
    if household is not None:
        queryset = queryset.filter(account__household=household)
    return queryset


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def month_end(value: date) -> date:
    return month_start(value) + relativedelta(months=1, days=-1)


def month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def month_label(value: date) -> str:
    return f"{MONTH_LABELS[value.month - 1]} {str(value.year)[2:]}"


def default_range(*, household=None) -> tuple[date, date]:
    """Current month until the prediction horizon, unless overridden in settings."""
    today = timezone.localdate()
    horizon = int(
        Setting.get(PREDICTION_HORIZON_MONTHS, 24, household=household) or 24
    )
    return month_start(today), month_end(today + relativedelta(months=horizon))


def quantize(value: Decimal | None) -> Decimal:
    return (value or ZERO).quantize(Decimal("0.01"))


@dataclass
class ProjectionRequest:
    date_from: date
    date_until: date
    account_ids: list[str] | None = None


def build_projection(
    date_from: date | None = None,
    date_until: date | None = None,
    account_ids: list[str] | None = None,
    household=None,
) -> dict:
    default_from, default_until = default_range(household=household)
    date_from = date_from or default_from
    date_until = date_until or default_until
    if date_until < date_from:
        date_from, date_until = date_until, date_from

    today = timezone.localdate()
    currency = Setting.get(CURRENCY, "EUR", household=household)

    accounts = Account.objects.filter(is_active=True, household=household)
    if account_ids:
        accounts = accounts.filter(pk__in=account_ids)
    accounts = list(accounts)
    account_pks = [account.pk for account in accounts]

    net_worth_accounts = [a for a in accounts if a.include_in_net_worth]
    opening_total = sum((a.opening_balance or ZERO) for a in net_worth_accounts) or ZERO

    base_queryset = counted_transactions(household=household).filter(account_id__in=account_pks)

    # --- running balance before the window ----------------------------------
    before = base_queryset.filter(
        booking_date__lt=date_from, account__include_in_net_worth=True
    ).aggregate(total=Sum("amount"))["total"] or ZERO
    running = opening_total + before

    # --- monthly buckets -----------------------------------------------------
    window = base_queryset.filter(booking_date__gte=date_from, booking_date__lte=date_until)
    reporting_window = window.filter(is_internal_transfer=False)

    income_by_month: dict[str, Decimal] = defaultdict(lambda: ZERO)
    expense_by_month: dict[str, Decimal] = defaultdict(lambda: ZERO)
    net_worth_by_month: dict[str, Decimal] = defaultdict(lambda: ZERO)

    rows = reporting_window.values("booking_date", "amount")
    for row in rows:
        key = month_key(row["booking_date"])
        amount = row["amount"] or ZERO
        if amount >= 0:
            income_by_month[key] += amount
        else:
            expense_by_month[key] += amount
    balance_rows = window.filter(account__include_in_net_worth=True).values(
        "booking_date", "amount"
    )
    for row in balance_rows:
        net_worth_by_month[month_key(row["booking_date"])] += row["amount"] or ZERO

    months: list[dict] = []
    cursor = month_start(date_from)
    last_day = month_start(date_until)
    while cursor <= last_day:
        key = month_key(cursor)
        income = quantize(income_by_month[key])
        expense = quantize(expense_by_month[key])
        running = running + net_worth_by_month[key]
        months.append(
            {
                "month": key,
                "label": month_label(cursor),
                "date": cursor.isoformat(),
                "income": str(income),
                "expense": str(abs(expense)),
                "net": str(quantize(income + expense)),
                "balance": str(quantize(running)),
                "is_past": month_end(cursor) < today,
                "is_current": month_start(today) == cursor,
            }
        )
        cursor += relativedelta(months=1)

    # --- totals & KPIs -------------------------------------------------------
    income_total = quantize(sum(income_by_month.values(), ZERO))
    expense_total = quantize(abs(sum(expense_by_month.values(), ZERO)))
    net_total = quantize(income_total - expense_total)
    month_count = max(len(months), 1)

    balance_today = quantize(
        opening_total
        + (
            counted_transactions(household=household)
            .filter(
                account_id__in=account_pks,
                account__include_in_net_worth=True,
                booking_date__lte=today,
            )
            .aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
    )
    booked_today = quantize(
        opening_total
        + (
            Transaction.objects.filter(
                account_id__in=account_pks,
                account__household=household,
                account__include_in_net_worth=True,
                state=Transaction.State.REALITY,
                booking_date__lte=today,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
    )

    projected_balance = Decimal(months[-1]["balance"]) if months else balance_today
    lowest = min(months, key=lambda m: Decimal(m["balance"])) if months else None

    savings_goal = Setting.get(SAVINGS_GOAL, 0, household=household)
    savings_goal = Decimal(str(savings_goal or 0))
    goal_date_raw = Setting.get(SAVINGS_GOAL_DATE, None, household=household)
    goal_reached_month = None
    if savings_goal > 0:
        for entry in months:
            if Decimal(entry["balance"]) >= savings_goal:
                goal_reached_month = entry["month"]
                break

    kpis = {
        "balance_today": str(balance_today),
        "booked_balance_today": str(booked_today),
        "income_total": str(income_total),
        "expense_total": str(expense_total),
        "net_total": str(net_total),
        "income_monthly_avg": str(quantize(income_total / month_count)),
        "expense_monthly_avg": str(quantize(expense_total / month_count)),
        "net_monthly_avg": str(quantize(net_total / month_count)),
        "savings_rate": str(
            quantize(net_total / income_total * 100) if income_total > 0 else ZERO
        ),
        "projected_balance": str(quantize(projected_balance)),
        "lowest_balance": lowest["balance"] if lowest else str(balance_today),
        "lowest_balance_month": lowest["month"] if lowest else None,
        "savings_goal": str(quantize(savings_goal)),
        "savings_goal_date": goal_date_raw,
        "savings_goal_reached_month": goal_reached_month,
        "savings_goal_progress": str(
            quantize(balance_today / savings_goal * 100) if savings_goal > 0 else ZERO
        ),
    }

    # --- category breakdown (expenses in the window) -------------------------
    category_rows = (
        reporting_window.filter(amount__lt=0)
        .values("category_id")
        .annotate(total=Sum("amount"))
        .order_by("total")
    )
    categories_by_id = {
        c.pk: c for c in Category.objects.filter(household=household)
    }
    breakdown = []
    for row in category_rows:
        category = categories_by_id.get(row["category_id"])
        if category is None:
            continue
        total = abs(quantize(row["total"]))
        breakdown.append(
            {
                "category": {
                    "id": str(category.pk),
                    "name": category.name,
                    "slug": category.slug,
                    "color": category.color,
                    "icon": category.icon,
                    "object_reference": category.object_reference,
                },
                "total": str(total),
                "share": str(
                    quantize(total / expense_total * 100) if expense_total > 0 else ZERO
                ),
            }
        )

    income_rows = (
        reporting_window.filter(amount__gte=0)
        .values("category_id")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    income_breakdown = []
    for row in income_rows:
        category = categories_by_id.get(row["category_id"])
        if category is None:
            continue
        total = quantize(row["total"])
        income_breakdown.append(
            {
                "category": {
                    "id": str(category.pk),
                    "name": category.name,
                    "slug": category.slug,
                    "color": category.color,
                    "icon": category.icon,
                    "object_reference": category.object_reference,
                },
                "total": str(total),
                "share": str(
                    quantize(total / income_total * 100) if income_total > 0 else ZERO
                ),
            }
        )

    # --- accounts ------------------------------------------------------------
    account_payload = []
    for account in accounts:
        account_payload.append(
            {
                "id": str(account.pk),
                "object_reference": account.object_reference,
                "name": account.name,
                "holder": account.holder,
                "kind": account.kind,
                "color": account.color,
                "currency": account.currency,
                "include_in_net_worth": account.include_in_net_worth,
                "balance_today": str(quantize(account.balance_at(today, include_planned=True))),
                "booked_balance": str(quantize(account.balance_at(today))),
                "balance_end": str(
                    quantize(account.balance_at(date_until, include_planned=True))
                ),
            }
        )

    return {
        "range": {
            "from": date_from.isoformat(),
            "until": date_until.isoformat(),
            "today": today.isoformat(),
            "months": len(months),
        },
        "currency": currency,
        "kpis": kpis,
        "months": months,
        "expenses_by_category": breakdown,
        "income_by_category": income_breakdown,
        "accounts": account_payload,
    }
