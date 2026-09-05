"""Query filters used by the expenses / income pages."""

from __future__ import annotations

import django_filters as filters

from finance.models import Contract, Job, Loan, Transaction


class TransactionFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="booking_date", lookup_expr="gte")
    date_until = filters.DateFilter(field_name="booking_date", lookup_expr="lte")
    min_amount = filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = filters.NumberFilter(field_name="amount", lookup_expr="lte")
    direction = filters.CharFilter(method="filter_direction")
    category = filters.CharFilter(field_name="category_id")
    account = filters.CharFilter(field_name="account_id")
    unmatched = filters.BooleanFilter(method="filter_unmatched")
    has_origin = filters.BooleanFilter(method="filter_has_origin")

    class Meta:
        model = Transaction
        fields = ["state", "source", "needs_review", "classified_by_ai"]

    def filter_direction(self, queryset, name: str, value: str):
        if value == "income":
            return queryset.filter(amount__gte=0, is_internal_transfer=False)
        if value == "expense":
            return queryset.filter(amount__lt=0, is_internal_transfer=False)
        return queryset

    def filter_unmatched(self, queryset, name: str, value: bool):
        return queryset.filter(matched_transaction__isnull=bool(value))

    def filter_has_origin(self, queryset, name: str, value: bool):
        from django.db.models import Q

        condition = Q(contract__isnull=False) | Q(loan__isnull=False) | Q(job__isnull=False)
        return queryset.filter(condition) if value else queryset.exclude(condition)


class RecurringFilter(filters.FilterSet):
    active_on = filters.DateFilter(method="filter_active_on")

    def filter_active_on(self, queryset, name: str, value):
        from django.db.models import Q

        return queryset.filter(
            Q(start_date__lte=value) & (Q(end_date__isnull=True) | Q(end_date__gte=value))
        )


class ContractFilter(RecurringFilter):
    class Meta:
        model = Contract
        fields = ["is_active", "account", "category", "interval", "contract_direction"]


class LoanFilter(RecurringFilter):
    class Meta:
        model = Loan
        fields = ["is_active", "account", "category", "interval"]


class JobFilter(RecurringFilter):
    class Meta:
        model = Job
        fields = ["is_active", "account", "category", "interval"]
