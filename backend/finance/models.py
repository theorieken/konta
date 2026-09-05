"""
Domain models of the household plan.

    Account       a bank account (or cash / credit card)
    Category      exactly one per transaction – the basis of every report
    Transaction   a past ("reality") or future ("planned") money movement
    Contract      something recurring that costs money (rent, insurance, …)
    Loan          borrowed money that is paid back in instalments
    Job           recurring income

Contract, Loan and Job are *sources*: celery beat materialises their future
occurrences as planned transactions up to the prediction horizon. When a CSV
import later brings in the real booking, the importer matches it against the
planned transaction instead of creating a duplicate.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterator

from dateutil.relativedelta import relativedelta
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from base.models import BaseModel, Household

ZERO = Decimal("0.00")


def clamp_day(year: int, month: int, day: int) -> date:
    """`clamp_day(2026, 2, 31)` -> 2026-02-28."""
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(day, 1), last))


class Direction(models.TextChoices):
    INCOME = "income", "Einnahme"
    EXPENSE = "expense", "Ausgabe"


class Interval(models.TextChoices):
    WEEKLY = "weekly", "wöchentlich"
    BIWEEKLY = "biweekly", "zweiwöchentlich"
    MONTHLY = "monthly", "monatlich"
    QUARTERLY = "quarterly", "vierteljährlich"
    SEMIANNUAL = "semiannual", "halbjährlich"
    YEARLY = "yearly", "jährlich"
    ONCE = "once", "einmalig"


# -----------------------------------------------------------------------------
# Account
# -----------------------------------------------------------------------------
class Account(BaseModel):
    household = models.ForeignKey(
        Household,
        verbose_name="Haushalt",
        on_delete=models.CASCADE,
        related_name="accounts",
        null=True,
        blank=True,
    )

    class Kind(models.TextChoices):
        CHECKING = "checking", "Girokonto"
        SAVINGS = "savings", "Sparkonto"
        CREDIT = "credit", "Kreditkarte"
        CASH = "cash", "Bargeld"
        INVESTMENT = "investment", "Depot"

    holder = models.CharField("Inhaber", max_length=255, blank=True, default="")
    kind = models.CharField("Art", max_length=16, choices=Kind.choices, default=Kind.CHECKING)
    iban = models.CharField("IBAN", max_length=34, blank=True, default="")
    bank_name = models.CharField("Bank", max_length=255, blank=True, default="")
    currency = models.CharField("Währung", max_length=8, default="EUR")
    color = models.CharField("Farbe", max_length=32, blank=True, default="")

    opening_balance = models.DecimalField(
        "Startsaldo", max_digits=14, decimal_places=2, default=ZERO
    )
    opening_balance_date = models.DateField("Startsaldo am", null=True, blank=True)

    include_in_net_worth = models.BooleanField("Im Gesamtvermögen", default=True)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        verbose_name = "Konto"
        verbose_name_plural = "Konten"
        ordering = ("name",)

    def balance_at(self, until: date | None = None, *, include_planned: bool = False) -> Decimal:
        """Opening balance plus every (matched-aware) transaction up to `until`."""
        queryset = self.transactions.all()
        if not include_planned:
            queryset = queryset.filter(state=Transaction.State.REALITY)
        else:
            queryset = queryset.exclude(
                state=Transaction.State.PLANNED, matched_transaction__isnull=False
            )
        if until is not None:
            queryset = queryset.filter(booking_date__lte=until)
        total = queryset.aggregate(total=models.Sum("amount"))["total"] or ZERO
        return (self.opening_balance or ZERO) + total


# -----------------------------------------------------------------------------
# Category
# -----------------------------------------------------------------------------
class Category(BaseModel):
    """
    Every transaction has exactly one category – that invariant is what makes
    the dashboard reports (top expenses, category breakdown) trivial.
    """

    class Kind(models.TextChoices):
        INCOME = "income", "Einnahme"
        EXPENSE = "expense", "Ausgabe"
        BOTH = "both", "Beides"

    household = models.ForeignKey(
        Household,
        verbose_name="Haushalt",
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )
    slug = models.SlugField("Kürzel", max_length=80)
    kind = models.CharField("Art", max_length=16, choices=Kind.choices, default=Kind.EXPENSE)
    color = models.CharField("Farbe", max_length=32, blank=True, default="")
    icon = models.CharField("Icon", max_length=64, blank=True, default="")
    parent = models.ForeignKey(
        "self", verbose_name="Oberkategorie", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="children",
    )
    keywords = models.JSONField(
        "Stichwörter", default=list, blank=True,
        help_text="Hinweise für die automatische Zuordnung beim CSV-Import.",
    )
    is_system = models.BooleanField("Standardkategorie", default=False)
    monthly_budget = models.DecimalField(
        "Monatsbudget", max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Kategorie"
        verbose_name_plural = "Kategorien"
        ordering = ("kind", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["household", "slug"], name="unique_category_slug_per_household"
            )
        ]

    def __str__(self) -> str:
        return self.name


# -----------------------------------------------------------------------------
# Recurring sources: Contract / Loan / Job
# -----------------------------------------------------------------------------
class RecurringSource(BaseModel):
    """Abstract parent of everything that generates planned transactions."""

    account = models.ForeignKey(
        Account, verbose_name="Konto", on_delete=models.CASCADE,
        related_name="%(class)ss",
    )
    category = models.ForeignKey(
        Category, verbose_name="Kategorie", on_delete=models.PROTECT,
        related_name="%(class)ss",
    )
    interval = models.CharField(
        "Intervall", max_length=16, choices=Interval.choices, default=Interval.MONTHLY
    )
    interval_count = models.PositiveSmallIntegerField(
        "Intervall-Faktor", default=1, validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    day_of_month = models.PositiveSmallIntegerField(
        "Tag im Monat", default=1, validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    start_date = models.DateField("Beginn")
    end_date = models.DateField("Ende", null=True, blank=True)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        abstract = True
        ordering = ("name",)

    # -- to be provided by subclasses ----------------------------------------
    @property
    def signed_amount(self) -> Decimal:
        raise NotImplementedError

    @property
    def direction(self) -> str:
        return Direction.INCOME if self.signed_amount >= 0 else Direction.EXPENSE

    # -- occurrence maths -----------------------------------------------------
    def _step(self) -> relativedelta | timedelta:
        factor = self.interval_count or 1
        return {
            Interval.WEEKLY: timedelta(weeks=1 * factor),
            Interval.BIWEEKLY: timedelta(weeks=2 * factor),
            Interval.MONTHLY: relativedelta(months=1 * factor),
            Interval.QUARTERLY: relativedelta(months=3 * factor),
            Interval.SEMIANNUAL: relativedelta(months=6 * factor),
            Interval.YEARLY: relativedelta(years=1 * factor),
        }.get(self.interval, relativedelta(months=1))

    def occurrences(self, until: date, since: date | None = None) -> Iterator[date]:
        """Every due date in `[since, until]`, capped by `end_date`."""
        if not self.is_active:
            return
        hard_end = min(until, self.end_date) if self.end_date else until
        if self.interval == Interval.ONCE:
            if self.start_date <= hard_end and (since is None or self.start_date >= since):
                yield self.start_date
            return

        current = self.start_date
        uses_month_day = self.interval in {
            Interval.MONTHLY, Interval.QUARTERLY, Interval.SEMIANNUAL, Interval.YEARLY,
        }
        if uses_month_day:
            current = clamp_day(current.year, current.month, self.day_of_month)
            if current < self.start_date:
                current = clamp_day(*_next_month(current), self.day_of_month)

        step = self._step()
        guard = 0
        while current <= hard_end and guard < 2000:
            guard += 1
            if since is None or current >= since:
                yield current
            nxt = current + step
            current = (
                clamp_day(nxt.year, nxt.month, self.day_of_month) if uses_month_day else nxt
            )

    def recurrence_key(self, due: date) -> str:
        """Stable identity of one generated transaction – prevents duplicates."""
        return f"{self._meta.db_table}:{self.pk}:{due.isoformat()}"


def _next_month(value: date) -> tuple[int, int]:
    return (value.year + 1, 1) if value.month == 12 else (value.year, value.month + 1)


class Contract(RecurringSource):
    """Rent, insurance, subscriptions – anything that costs money regularly."""

    provider = models.CharField("Anbieter", max_length=255, blank=True, default="")
    amount = models.DecimalField("Betrag", max_digits=14, decimal_places=2, default=ZERO)
    contract_direction = models.CharField(
        "Richtung", max_length=16, choices=Direction.choices, default=Direction.EXPENSE
    )
    contract_number = models.CharField("Vertragsnummer", max_length=120, blank=True, default="")
    cancellation_period_days = models.PositiveSmallIntegerField("Kündigungsfrist (Tage)", default=0)

    class Meta:
        verbose_name = "Vertrag"
        verbose_name_plural = "Verträge"
        ordering = ("name",)

    @property
    def signed_amount(self) -> Decimal:
        magnitude = abs(self.amount or ZERO)
        return magnitude if self.contract_direction == Direction.INCOME else -magnitude

    @property
    def monthly_equivalent(self) -> Decimal:
        """Normalised to a month so contracts stay comparable in the UI."""
        factor = {
            Interval.WEEKLY: Decimal("4.345"),
            Interval.BIWEEKLY: Decimal("2.173"),
            Interval.MONTHLY: Decimal("1"),
            Interval.QUARTERLY: Decimal("1") / Decimal("3"),
            Interval.SEMIANNUAL: Decimal("1") / Decimal("6"),
            Interval.YEARLY: Decimal("1") / Decimal("12"),
            Interval.ONCE: Decimal("0"),
        }.get(self.interval, Decimal("1"))
        return (self.signed_amount * factor / Decimal(self.interval_count or 1)).quantize(
            Decimal("0.01")
        )

    @property
    def next_cancellation_date(self) -> date | None:
        if not self.end_date or not self.cancellation_period_days:
            return None
        return self.end_date - timedelta(days=self.cancellation_period_days)


class Loan(RecurringSource):
    """Borrowed money paid back in instalments."""

    lender = models.CharField("Kreditgeber", max_length=255, blank=True, default="")
    principal = models.DecimalField("Kreditsumme", max_digits=14, decimal_places=2, default=ZERO)
    interest_rate = models.DecimalField(
        "Zinssatz (% p. a.)", max_digits=6, decimal_places=3, default=ZERO
    )
    instalment = models.DecimalField("Rate", max_digits=14, decimal_places=2, default=ZERO)
    remaining_at_start = models.DecimalField(
        "Restschuld bei Beginn", max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Kredit"
        verbose_name_plural = "Kredite"
        ordering = ("name",)

    @property
    def signed_amount(self) -> Decimal:
        return -abs(self.instalment or ZERO)

    @property
    def paid_so_far(self) -> Decimal:
        total = self.transactions.filter(state=Transaction.State.REALITY).aggregate(
            total=models.Sum("amount")
        )["total"] or ZERO
        return abs(total)

    @property
    def outstanding(self) -> Decimal:
        base = self.remaining_at_start if self.remaining_at_start is not None else self.principal
        return max((base or ZERO) - self.paid_so_far, ZERO)


class Job(RecurringSource):
    """A regular income – salary, pension, freelance retainer."""

    employer = models.CharField("Arbeitgeber", max_length=255, blank=True, default="")
    gross_amount = models.DecimalField("Brutto", max_digits=14, decimal_places=2, default=ZERO)
    net_amount = models.DecimalField("Netto", max_digits=14, decimal_places=2, default=ZERO)
    tax_class = models.CharField("Steuerklasse", max_length=8, blank=True, default="")
    part_time_factor = models.DecimalField(
        "Teilzeitquote", max_digits=5, decimal_places=4, default=Decimal("1.0000"),
        help_text="1.0 = Vollzeit, 0.75 = 75 %.",
    )

    class Meta:
        verbose_name = "Einkommen"
        verbose_name_plural = "Einkommen"
        ordering = ("name",)

    @property
    def signed_amount(self) -> Decimal:
        return abs(self.net_amount or ZERO)


# -----------------------------------------------------------------------------
# Transaction
# -----------------------------------------------------------------------------
class Transaction(BaseModel):
    """
    One money movement.

    `amount` is *signed*: income is positive, an expense is negative. That way
    every balance is a plain SUM and the dashboard needs no case distinctions.
    """

    class State(models.TextChoices):
        REALITY = "reality", "Gebucht"
        PLANNED = "planned", "Geplant"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manuell"
        IMPORT = "import", "Import"
        GENERATED = "generated", "Automatisch"

    account = models.ForeignKey(
        Account, verbose_name="Konto", on_delete=models.CASCADE, related_name="transactions"
    )
    category = models.ForeignKey(
        Category, verbose_name="Kategorie", on_delete=models.PROTECT,
        related_name="transactions",
        help_text="Jede Transaktion hat genau eine Kategorie.",
    )

    amount = models.DecimalField(
        "Betrag", max_digits=14, decimal_places=2,
        help_text="Positiv = Einnahme, negativ = Ausgabe.",
    )
    booking_date = models.DateField("Datum", db_index=True)
    state = models.CharField(
        "Status", max_length=16, choices=State.choices, default=State.PLANNED, db_index=True
    )
    source = models.CharField(
        "Herkunft", max_length=16, choices=Source.choices, default=Source.MANUAL
    )

    counterparty = models.CharField("Gegenseite", max_length=255, blank=True, default="")
    purpose = models.TextField("Verwendungszweck", blank=True, default="")

    # -- origin: which recurring source produced this transaction -------------
    contract = models.ForeignKey(
        Contract, verbose_name="Vertrag", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="transactions",
    )
    loan = models.ForeignKey(
        Loan, verbose_name="Kredit", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="transactions",
    )
    job = models.ForeignKey(
        Job, verbose_name="Einkommen", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="transactions",
    )
    recurrence_key = models.CharField(
        "Wiederholungsschlüssel", max_length=200, blank=True, default="", db_index=True
    )

    # -- import provenance ----------------------------------------------------
    import_file = models.ForeignKey(
        "base.File", verbose_name="Importdatei", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="transactions",
    )
    external_id = models.CharField("Externe ID", max_length=200, blank=True, default="")
    import_hash = models.CharField("Import-Hash", max_length=64, blank=True, default="", db_index=True)

    # -- matching planned <-> reality -----------------------------------------
    matched_transaction = models.ForeignKey(
        "self", verbose_name="Abgeglichen mit", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="matches",
    )

    # -- transfers between two accounts in the same household ----------------
    is_internal_transfer = models.BooleanField("Interne Umbuchung", default=False, db_index=True)
    transfer_pair = models.ForeignKey(
        "self",
        verbose_name="Gegenbuchung",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transfer_matches",
    )

    # -- AI classification ----------------------------------------------------
    classified_by_ai = models.BooleanField("KI-Kategorie", default=False)
    classification_confidence = models.FloatField("Konfidenz", null=True, blank=True)
    classification_note = models.CharField("Begründung", max_length=500, blank=True, default="")
    needs_review = models.BooleanField("Prüfen", default=False, db_index=True)

    class Meta:
        verbose_name = "Transaktion"
        verbose_name_plural = "Transaktionen"
        ordering = ("-booking_date", "-created_at")
        indexes = [
            models.Index(fields=["booking_date", "state"]),
            models.Index(fields=["account", "booking_date"]),
            models.Index(fields=["category", "booking_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recurrence_key"],
                condition=models.Q(recurrence_key__gt="", deleted_at__isnull=True),
                name="unique_generated_transaction",
            ),
            models.UniqueConstraint(
                fields=["account", "import_hash"],
                condition=models.Q(import_hash__gt="", deleted_at__isnull=True),
                name="unique_imported_transaction",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.booking_date} {self.display_name} {self.amount}"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.counterparty or (self.purpose or "")[:80] or "Transaktion"
        super().save(*args, **kwargs)

    # -- derived --------------------------------------------------------------
    @property
    def direction(self) -> str:
        return Direction.INCOME if (self.amount or ZERO) >= 0 else Direction.EXPENSE

    @property
    def is_planned(self) -> bool:
        return self.state == self.State.PLANNED

    @property
    def is_matched(self) -> bool:
        return self.matched_transaction_id is not None

    @property
    def origin_reference(self) -> str:
        """Object reference of the Contract/Loan/Job that generated this row."""
        for field, obj in (
            ("contract", self.contract), ("loan", self.loan), ("job", self.job)
        ):
            if obj is not None:
                return obj.object_reference
        return ""

    @property
    def is_auto_categorised(self) -> bool:
        """
        True while the category still comes from the classifier (AI or the
        keyword fallback). A manual correction clears the classification
        metadata, which is how we know never to overwrite the user again.
        """
        return bool(self.classified_by_ai or self.classification_note)

    @property
    def counts_towards_projection(self) -> bool:
        """A planned transaction that already happened must not be counted twice."""
        return not (self.is_planned and self.is_matched)
