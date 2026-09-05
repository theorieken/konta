from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from base.serializers import BaseSerializer, register_serializer
from finance.models import Account, Category, Contract, Direction, Job, Loan, Transaction


class ObjectRefField(serializers.Field):
    """Read-only ``{id, name, object_reference, …}`` stub for related objects."""

    def __init__(self, *extra_fields: str, **kwargs):
        kwargs.setdefault("read_only", True)
        self.extra_fields = extra_fields
        super().__init__(**kwargs)

    def to_representation(self, value) -> dict[str, Any] | None:
        if value is None:
            return None
        payload = {
            "id": str(value.pk),
            "name": value.display_name,
            "object_reference": value.object_reference,
        }
        for field in self.extra_fields:
            payload[field] = getattr(value, field, None)
        return payload


@register_serializer
class AccountSerializer(BaseSerializer):
    balance_today = serializers.SerializerMethodField()
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = BaseSerializer.BASE_FIELDS + (
            "holder",
            "kind",
            "iban",
            "bank_name",
            "currency",
            "color",
            "opening_balance",
            "opening_balance_date",
            "include_in_net_worth",
            "is_active",
            "balance_today",
            "transaction_count",
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS

    def get_balance_today(self, obj: Account) -> str:
        """Bounded by today – without the date the whole future plan would be
        summed into a field that claims to be the current balance."""
        from django.utils import timezone

        return str(obj.balance_at(timezone.localdate(), include_planned=True))

    def get_transaction_count(self, obj: Account) -> int:
        return obj.transactions.count()


@register_serializer
class CategorySerializer(BaseSerializer):
    parent_detail = ObjectRefField(source="parent", read_only=True)
    transaction_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = BaseSerializer.BASE_FIELDS + (
            "slug",
            "kind",
            "color",
            "icon",
            "parent",
            "parent_detail",
            "keywords",
            "is_system",
            "monthly_budget",
            "transaction_count",
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS + ("is_system",)
        extra_kwargs = {"slug": {"required": False}}

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request = self.context.get("request")
        household = getattr(request.user, "current_household", None) if request else None
        parent = attrs.get("parent")
        if parent is not None and parent.household_id != getattr(household, "pk", None):
            raise serializers.ValidationError({"parent": "Diese Kategorie gehört zu einem anderen Haushalt."})
        if not attrs.get("slug") and attrs.get("name"):
            from django.utils.text import slugify

            base_slug = slugify(attrs["name"])[:70] or "kategorie"
            slug = base_slug
            suffix = 2
            while Category.all_objects.filter(household=household, slug=slug).exclude(pk=self.instance.pk if self.instance else None).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            attrs["slug"] = slug
        return attrs


class RecurringSourceSerializer(BaseSerializer):
    """Shared fields of Contract, Loan and Job."""

    account_detail = ObjectRefField(source="account", read_only=True)
    category_detail = ObjectRefField("color", "icon", "slug", source="category", read_only=True)
    next_due_date = serializers.SerializerMethodField()
    planned_count = serializers.SerializerMethodField()

    RECURRING_FIELDS = (
        "account",
        "account_detail",
        "category",
        "category_detail",
        "interval",
        "interval_count",
        "day_of_month",
        "start_date",
        "end_date",
        "is_active",
        "next_due_date",
        "planned_count",
    )

    def get_next_due_date(self, obj) -> str | None:
        from django.utils import timezone

        from finance.services.generator import horizon_date

        today = timezone.localdate()
        for due in obj.occurrences(
            until=horizon_date(household=obj.account.household), since=today
        ):
            return due.isoformat()
        return None

    def get_planned_count(self, obj) -> int:
        return obj.transactions.filter(state=Transaction.State.PLANNED).count()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request = self.context.get("request")
        household = getattr(request.user, "current_household", None) if request else None
        for field in ("account", "category"):
            value = attrs.get(field) or getattr(self.instance, field, None)
            if value is not None and value.household_id != getattr(household, "pk", None):
                raise serializers.ValidationError({field: "Dieses Objekt gehört zu einem anderen Haushalt."})
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "Das Ende darf nicht vor dem Beginn liegen."}
            )
        return attrs


@register_serializer
class ContractSerializer(RecurringSourceSerializer):
    monthly_equivalent = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = (
            BaseSerializer.BASE_FIELDS
            + RecurringSourceSerializer.RECURRING_FIELDS
            + (
                "provider",
                "amount",
                "contract_direction",
                "contract_number",
                "cancellation_period_days",
                "monthly_equivalent",
            )
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS

    def get_monthly_equivalent(self, obj: Contract) -> str:
        return str(obj.monthly_equivalent)

    def validate_amount(self, value: Decimal) -> Decimal:
        if value is None or value == 0:
            raise serializers.ValidationError("Bitte einen Betrag angeben.")
        return abs(value)


@register_serializer
class LoanSerializer(RecurringSourceSerializer):
    outstanding = serializers.SerializerMethodField()
    paid_so_far = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = (
            BaseSerializer.BASE_FIELDS
            + RecurringSourceSerializer.RECURRING_FIELDS
            + (
                "lender",
                "principal",
                "interest_rate",
                "instalment",
                "remaining_at_start",
                "outstanding",
                "paid_so_far",
            )
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS

    def get_outstanding(self, obj: Loan) -> str:
        return str(obj.outstanding)

    def get_paid_so_far(self, obj: Loan) -> str:
        return str(obj.paid_so_far)

    def validate_instalment(self, value: Decimal) -> Decimal:
        if value is None or value == 0:
            raise serializers.ValidationError("Bitte eine Rate angeben.")
        return abs(value)


@register_serializer
class JobSerializer(RecurringSourceSerializer):
    class Meta:
        model = Job
        fields = (
            BaseSerializer.BASE_FIELDS
            + RecurringSourceSerializer.RECURRING_FIELDS
            + (
                "employer",
                "gross_amount",
                "net_amount",
                "tax_class",
                "part_time_factor",
            )
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS

    def validate_net_amount(self, value: Decimal) -> Decimal:
        if value is None or value == 0:
            raise serializers.ValidationError("Bitte das Nettoeinkommen angeben.")
        return abs(value)


@register_serializer
class TransactionSerializer(BaseSerializer):
    account_detail = ObjectRefField("color", "kind", source="account", read_only=True)
    category_detail = ObjectRefField("color", "icon", "slug", source="category", read_only=True)
    direction = serializers.CharField(read_only=True)
    origin_reference = serializers.CharField(read_only=True)
    is_matched = serializers.BooleanField(read_only=True)

    class Meta:
        model = Transaction
        fields = BaseSerializer.BASE_FIELDS + (
            "account",
            "account_detail",
            "category",
            "category_detail",
            "amount",
            "booking_date",
            "state",
            "source",
            "direction",
            "counterparty",
            "purpose",
            "contract",
            "loan",
            "job",
            "origin_reference",
            "recurrence_key",
            "import_file",
            "external_id",
            "matched_transaction",
            "is_matched",
            "is_internal_transfer",
            "transfer_pair",
            "classified_by_ai",
            "classification_confidence",
            "classification_note",
            "needs_review",
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS + (
            "recurrence_key",
            "import_file",
            "external_id",
            "origin_reference",
            "direction",
            "is_matched",
            "is_internal_transfer",
            "transfer_pair",
        )

    def validate_amount(self, value: Decimal) -> Decimal:
        if value is None or value == 0:
            raise serializers.ValidationError("Ein Betrag von 0 ergibt keinen Sinn.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        The UI sends a positive amount plus a direction; the database stores a
        signed amount. Doing the conversion here keeps the forms simple.
        """
        direction = self.initial_data.get("direction") if hasattr(self, "initial_data") else None
        request = self.context.get("request")
        household = getattr(request.user, "current_household", None) if request else None
        for field in ("account", "category"):
            value = attrs.get(field) or getattr(self.instance, field, None)
            if value is not None and value.household_id != getattr(household, "pk", None):
                raise serializers.ValidationError({field: "Dieses Objekt gehört zu einem anderen Haushalt."})
        amount = attrs.get("amount")
        if direction and amount is not None:
            magnitude = abs(amount)
            attrs["amount"] = magnitude if direction == Direction.INCOME else -magnitude
        if not attrs.get("category") and self.instance is None:
            raise serializers.ValidationError(
                {"category": "Jede Transaktion braucht eine Kategorie."}
            )
        # A category the user picked is final – drop the classifier metadata so
        # neither a re-run nor the plan matcher overwrites it later.
        if "category" in attrs and self.instance is not None:
            if attrs["category"] != self.instance.category:
                attrs["classified_by_ai"] = False
                attrs["classification_confidence"] = None
                attrs["classification_note"] = ""
                attrs["needs_review"] = False
        return attrs


class TransactionBulkCategorySerializer(serializers.Serializer):
    """`POST /api/transactions/bulk-category/`"""

    transactions = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())


class ProjectionQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_until = serializers.DateField(required=False)
    accounts = serializers.CharField(required=False, allow_blank=True)
