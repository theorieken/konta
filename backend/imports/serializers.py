from __future__ import annotations

from rest_framework import serializers

from base.models import File
from finance.models import Account


class TransactionImportSerializer(serializers.Serializer):
    """Upload payload of `POST /api/imports/transactions/` (multipart)."""

    file = serializers.FileField()
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), required=False, allow_null=True
    )
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_file(self, value):
        name = (value.name or "").lower()
        if not name.endswith((".csv", ".txt", ".tsv", ".fin")):
            raise serializers.ValidationError(
                "Bitte eine CSV-Datei oder eine .fin-Sicherung hochladen."
            )
        from django.conf import settings

        if value.size and value.size > getattr(settings, "MAX_UPLOAD_SIZE", 64 * 1024 * 1024):
            raise serializers.ValidationError("Die Datei ist zu groß.")
        return value

    def validate(self, attrs):
        upload = attrs.get("file")
        is_backup = bool(upload and (upload.name or "").lower().endswith(".fin"))
        if not is_backup and attrs.get("account") is None:
            raise serializers.ValidationError(
                {"account": "Für einen CSV-Import muss ein Konto gewählt werden."}
            )
        request = self.context.get("request")
        account = attrs.get("account")
        if request:
            from base.households import active_household

            household = active_household(request.user)
        else:
            household = None
        if account is not None and account.household_id != getattr(household, "id", None):
            raise serializers.ValidationError({"account": "Dieses Konto gehört zu einem anderen Haushalt."})
        return attrs

    def create(self, validated_data) -> File:
        upload = validated_data["file"]
        request = self.context.get("request")
        from base.households import active_household

        household = active_household(request.user) if request else None
        is_backup = (upload.name or "").lower().endswith(".fin")
        return File.objects.create(
            name=validated_data.get("name") or upload.name,
            file=upload,
            original_name=upload.name,
            content_type=(
                "application/x-fin-household"
                if is_backup
                else (getattr(upload, "content_type", "") or "text/csv")
            ),
            size=getattr(upload, "size", 0) or 0,
            purpose=(
                File.Purpose.BACKUP_IMPORT
                if is_backup
                else File.Purpose.TRANSACTION_IMPORT
            ),
            status=File.Status.PENDING,
            account=validated_data.get("account"),
            household=household,
            created_by=request.user if request and request.user.is_authenticated else None,
        )


class ReclassifySerializer(serializers.Serializer):
    transactions = serializers.ListField(child=serializers.UUIDField(), required=False)
    only_review = serializers.BooleanField(required=False, default=True)


class CommitImportSerializer(serializers.Serializer):
    confirm_restore = serializers.BooleanField(required=False, default=False)
