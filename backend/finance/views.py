"""REST endpoints for accounts, categories, transactions and recurring sources."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from base.events import broadcast_object
from base.households import active_household
from base.permissions import IsAuthenticatedHousehold
from base.queue import enqueue
from base.views import BaseViewSet
from finance.filters import ContractFilter, JobFilter, LoanFilter, TransactionFilter
from finance.models import Account, Category, Contract, Job, Loan, Transaction
from finance.serializers import (
    AccountSerializer,
    CategorySerializer,
    ContractSerializer,
    JobSerializer,
    LoanSerializer,
    ProjectionQuerySerializer,
    TransactionBulkCategorySerializer,
    TransactionSerializer,
)


class AccountViewSet(BaseViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    filterset_fields = ["kind", "is_active", "include_in_net_worth"]
    search_fields = ["name", "holder", "bank_name", "iban"]
    ordering_fields = ["name", "created_at"]

    @action(detail=True, methods=["get"], url_path="balance")
    def balance(self, request, pk: str | None = None) -> Response:
        account = self.get_object()
        until = request.query_params.get("until")
        until_date = date.fromisoformat(until) if until else None
        return Response(
            {
                "booked": str(account.balance_at(until_date)),
                "projected": str(account.balance_at(until_date, include_planned=True)),
            }
        )


class CategoryViewSet(BaseViewSet):
    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    filterset_fields = ["kind", "is_system", "parent"]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "kind", "created_at"]

    def get_queryset(self):
        return super().get_queryset().annotate(transaction_count=Count("transactions"))

    def perform_destroy(self, instance: Category) -> None:
        """A category that is still in use may not disappear silently."""
        if instance.transactions.exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"detail": "Diese Kategorie wird noch von Transaktionen verwendet."}
            )
        super().perform_destroy(instance)


class TransactionViewSet(BaseViewSet):
    queryset = Transaction.objects.select_related(
        "account", "category", "contract", "loan", "job"
    ).all()
    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter
    search_fields = ["name", "counterparty", "purpose", "external_id"]
    ordering_fields = ["booking_date", "amount", "created_at", "name"]
    ordering = ("-booking_date", "-created_at")

    def get_queryset(self):
        """
        A planned transaction that a real booking already fulfilled is
        superseded: it is kept for the audit trail but hidden from lists and
        totals, exactly like `projection.counted_transactions()` does. Without
        this, rent would appear – and be summed – twice in the same month.

        Pass `?include_superseded=true` to see them anyway; retrieving one by
        id or through /api/objects/ always works.
        """
        queryset = super().get_queryset()
        if self.action not in ("list", "summary"):
            return queryset
        raw = str(self.request.query_params.get("include_superseded", "")).lower()
        if raw in ("1", "true", "yes"):
            return queryset
        return queryset.exclude(
            state=Transaction.State.PLANNED, matched_transaction__isnull=False
        )

    def perform_create(self, serializer) -> None:
        instance = serializer.save()
        broadcast_object(instance, "created")
        # A manually booked transaction may fulfil an existing plan.
        if instance.state == Transaction.State.REALITY:
            from finance.services.matching import match_transaction

            match_transaction(instance)

    @action(detail=False, methods=["post"], url_path="bulk-category")
    def bulk_category(self, request) -> Response:
        """Re-categorise many transactions at once (used by the review list)."""
        serializer = TransactionBulkCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.validated_data["category"]
        ids = serializer.validated_data["transactions"]
        updated = Transaction.objects.filter(pk__in=ids).update(
            category=category,
            needs_review=False,
            classified_by_ai=False,
            classification_confidence=None,
            classification_note="",
        )
        return Response({"updated": updated, "category": str(category.pk)})

    @action(detail=True, methods=["post"], url_path="match")
    def match(self, request, pk: str | None = None) -> Response:
        """Manually trigger the planned/reality match for one transaction."""
        from finance.services.matching import match_transaction

        instance = self.get_object()
        matched = match_transaction(instance)
        return Response(
            {
                "matched": matched.object_reference if matched else None,
                "transaction": self.get_serializer(instance).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request) -> Response:
        """Totals for the current filter – powers the list headers."""
        queryset = self.filter_queryset(self.get_queryset())
        aggregate = queryset.aggregate(
            income=Sum("amount", filter=Q(amount__gte=0)),
            expense=Sum("amount", filter=Q(amount__lt=0)),
            count=Count("id"),
        )
        cents = Decimal("0.01")
        income = (aggregate["income"] or Decimal("0")).quantize(cents)
        expense = abs(aggregate["expense"] or Decimal("0")).quantize(cents)
        return Response(
            {
                "count": aggregate["count"],
                "income": str(income),
                "expense": str(expense),
                "net": str((income - expense).quantize(cents)),
            }
        )


class RecurringViewSet(BaseViewSet):
    """
    Shared behaviour of Contract / Loan / Job: whenever a source changes, its
    future planned transactions are rebuilt so the projection stays truthful.
    """

    def _resync(self, instance) -> None:
        from finance.tasks import resync_source

        enqueue(resync_source, instance._meta.db_table, str(instance.pk))

    def perform_create(self, serializer) -> None:
        instance = serializer.save()
        broadcast_object(instance, "created")
        self._resync(instance)

    def perform_update(self, serializer) -> None:
        instance = serializer.save()
        broadcast_object(instance, "updated")
        self._resync(instance)

    def perform_destroy(self, instance) -> None:
        from finance.services.generator import clear_future_planned

        clear_future_planned(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate(self, request, pk: str | None = None) -> Response:
        from finance.services.generator import resync_source as resync

        instance = self.get_object()
        removed, created = resync(instance)
        return Response({"removed": removed, "created": created})

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk: str | None = None) -> Response:
        """The next due dates without writing anything – used by the forms."""
        from finance.services.generator import horizon_date

        instance = self.get_object()
        limit = int(request.query_params.get("limit", 12))
        dates = []
        for due in instance.occurrences(
            until=horizon_date(household=instance.account.household)
        ):
            dates.append(due.isoformat())
            if len(dates) >= limit:
                break
        return Response({"amount": str(instance.signed_amount), "dates": dates})


class ContractViewSet(RecurringViewSet):
    queryset = Contract.objects.select_related("account", "category").all()
    serializer_class = ContractSerializer
    filterset_class = ContractFilter
    search_fields = ["name", "provider", "contract_number"]
    ordering_fields = ["name", "amount", "start_date", "created_at"]


class LoanViewSet(RecurringViewSet):
    queryset = Loan.objects.select_related("account", "category").all()
    serializer_class = LoanSerializer
    filterset_class = LoanFilter
    search_fields = ["name", "lender"]
    ordering_fields = ["name", "instalment", "start_date", "created_at"]


class JobViewSet(RecurringViewSet):
    queryset = Job.objects.select_related("account", "category").all()
    serializer_class = JobSerializer
    filterset_class = JobFilter
    search_fields = ["name", "employer"]
    ordering_fields = ["name", "net_amount", "start_date", "created_at"]


class DashboardView(APIView):
    """
    `/api/dashboard/?date_from=…&date_until=…&accounts=uuid,uuid`

    One request, everything the dashboard renders.
    """

    permission_classes = [IsAuthenticatedHousehold]

    def get(self, request) -> Response:
        from finance.services.projection import build_projection

        query = ProjectionQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data

        raw_accounts = (data.get("accounts") or "").strip()
        account_ids = [item for item in raw_accounts.split(",") if item] or None

        return Response(
            build_projection(
                date_from=data.get("date_from"),
                date_until=data.get("date_until"),
                account_ids=account_ids,
                household=active_household(request.user),
            )
        )


class PlanRegenerateView(APIView):
    """`POST /api/plan/regenerate/` – rebuild the whole plan on demand."""

    permission_classes = [IsAuthenticatedHousehold]

    def post(self, request) -> Response:
        from finance.services.generator import generate_all
        from finance.services.matching import match_unmatched

        months = request.data.get("months")
        household = active_household(request.user)
        result = generate_all(int(months) if months else None, household=household).as_dict()
        result["matching"] = match_unmatched(household=household)
        return Response(result, status=status.HTTP_200_OK)
