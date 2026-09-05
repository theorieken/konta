from django.contrib import admin

from base.admin import BaseAdmin
from finance.models import Account, Category, Contract, Job, Loan, Transaction


@admin.register(Account)
class AccountAdmin(BaseAdmin):
    list_display = ("name", "holder", "kind", "opening_balance", "is_active")
    list_filter = ("kind", "is_active", "include_in_net_worth")
    search_fields = ("name", "holder", "iban", "bank_name")


@admin.register(Category)
class CategoryAdmin(BaseAdmin):
    list_display = ("name", "slug", "kind", "is_system")
    list_filter = ("kind", "is_system")
    search_fields = ("name", "slug")


class RecurringAdmin(BaseAdmin):
    list_filter = ("is_active", "interval", "account", "category")
    search_fields = ("name",)
    date_hierarchy = "start_date"


@admin.register(Contract)
class ContractAdmin(RecurringAdmin):
    list_display = ("name", "provider", "amount", "interval", "account", "is_active")


@admin.register(Loan)
class LoanAdmin(RecurringAdmin):
    list_display = ("name", "lender", "instalment", "principal", "account", "is_active")


@admin.register(Job)
class JobAdmin(RecurringAdmin):
    list_display = ("name", "employer", "net_amount", "account", "is_active")


@admin.register(Transaction)
class TransactionAdmin(BaseAdmin):
    list_display = (
        "booking_date", "name", "amount", "state", "category", "account", "needs_review",
    )
    list_filter = ("state", "source", "needs_review", "classified_by_ai", "account", "category")
    search_fields = ("name", "counterparty", "purpose", "external_id")
    date_hierarchy = "booking_date"
    autocomplete_fields = ("account", "category")
