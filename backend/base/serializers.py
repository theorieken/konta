"""
Serialization layer.

Every serializer in this project inherits from `BaseSerializer`, which embeds a
standard `_meta` block into each object:

    {
      "id": "…",
      "name": "Miete Wohnung",
      "…model fields…": …,
      "_meta": {
        "object_reference": "finance_transaction-1b2c…",
        "db_table": "finance_transaction",
        "model": "finance.transaction",
        "verbose_name": "Transaktion",
        "name": "Miete Wohnung",
        "created_at": "…", "updated_at": "…", "deleted_at": null,
        "created_by": {"id": "…", "name": "Theo"},
        "tags": [{"id": "…", "name": "fix", "color": "#8ab"}],
        "api_url": "/api/objects/finance_transaction-1b2c…/",
        "frontend_url": "/objects/finance_transaction-1b2c…"
      }
    }

The frontend relies on `_meta` for the object drawer, the generic object page
and for rendering tags, so never strip it from a response.
"""

from __future__ import annotations

from typing import Any, Type

from rest_framework import serializers

from base.models import BaseModel, File, Household, Setting, Tag

# db_table -> serializer class, filled by @register_serializer.
SERIALIZER_REGISTRY: dict[str, Type["BaseSerializer"]] = {}


def register_serializer(serializer_class: Type["BaseSerializer"]) -> Type["BaseSerializer"]:
    """Class decorator that makes a serializer discoverable by the generic API."""
    model = serializer_class.Meta.model
    SERIALIZER_REGISTRY[model._meta.db_table] = serializer_class
    return serializer_class


def load_all_serializers() -> None:
    """Import every serializer module so the registry is complete."""
    from importlib import import_module

    for module in ("base.serializers", "users.serializers", "finance.serializers",
                   "imports.serializers"):
        try:
            import_module(module)
        except ModuleNotFoundError:  # pragma: no cover - optional app
            continue


class TagSerializer(serializers.ModelSerializer):
    """Lightweight tag representation used inside `_meta`."""

    target_reference = serializers.CharField(read_only=True)

    class Meta:
        model = Tag
        fields = ("id", "name", "color", "db_table", "object_uuid", "target_reference")
        read_only_fields = ("id", "target_reference")


class BaseSerializer(serializers.ModelSerializer):
    """
    Parent of every model serializer.

    Subclasses only declare their own fields; `BASE_FIELDS` and
    `BASE_READ_ONLY_FIELDS` are meant to be spliced into `Meta.fields`.
    """

    BASE_FIELDS = ("id", "name", "notes", "created_at", "updated_at", "created_by", "_meta")
    BASE_READ_ONLY_FIELDS = ("id", "created_at", "updated_at", "created_by", "_meta")

    _meta = serializers.SerializerMethodField(method_name="get_object_meta")

    # -- _meta ---------------------------------------------------------------
    def get_object_meta(self, obj: BaseModel) -> dict[str, Any]:
        payload = obj.meta_payload()
        payload["created_by"] = self._user_summary(getattr(obj, "created_by", None))
        payload["tags"] = TagSerializer(self._tags_for(obj), many=True).data
        payload["api_url"] = f"/api/objects/{obj.object_reference}/"
        payload["frontend_url"] = f"/objects/{obj.object_reference}"
        return payload

    @staticmethod
    def _user_summary(user) -> dict[str, Any] | None:
        if user is None:
            return None
        return {
            "id": str(user.pk),
            "name": getattr(user, "display_name", None) or str(user),
            "object_reference": getattr(user, "object_reference", None),
        }

    def _tags_for(self, obj: BaseModel):
        """Uses a prefetched map when the viewset provided one (avoids N+1)."""
        tag_map = self.context.get("tag_map")
        if tag_map is not None:
            return tag_map.get(obj.object_reference, [])
        return list(Tag.objects.for_object(obj))

    # -- write behaviour ------------------------------------------------------
    def create(self, validated_data: dict[str, Any]):
        request = self.context.get("request")
        if request is not None and getattr(request.user, "is_authenticated", False):
            validated_data.setdefault("created_by", request.user)
            field_names = {field.name for field in self.Meta.model._meta.get_fields()}
            if "household" in field_names:
                from base.households import active_household

                validated_data.setdefault("household", active_household(request.user))
        return super().create(validated_data)


@register_serializer
class HouseholdSerializer(BaseSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = BaseSerializer.BASE_FIELDS + ("member_count",)
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS + ("member_count",)

    def get_member_count(self, obj: Household) -> int:
        return obj.members.count()


@register_serializer
class TagWriteSerializer(BaseSerializer):
    """Full tag serializer exposed at `/api/tags/`."""

    target_reference = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Tag
        fields = BaseSerializer.BASE_FIELDS + (
            "db_table",
            "object_uuid",
            "color",
            "target_reference",
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS
        extra_kwargs = {
            "db_table": {"required": False},
            "object_uuid": {"required": False},
        }
        # The database constraint is validated after `target_reference` has
        # been resolved below. DRF's generated validator runs too early and
        # incorrectly requires the two derived fields in the request body.
        validators = []

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        reference = attrs.pop("target_reference", "")
        if reference:
            from base.registry import get_model_for_table, split_reference

            db_table, object_uuid = split_reference(reference)
            model = get_model_for_table(db_table)  # raises for unknown tables
            target = model.objects.filter(pk=object_uuid).first()
            request = self.context.get("request")
            if request is not None:
                from base.households import active_household, belongs_to_household

                if target is None or not belongs_to_household(
                    target, active_household(request.user)
                ):
                    raise serializers.ValidationError(
                        {"target_reference": "Objekt nicht gefunden."}
                    )
            attrs["db_table"] = db_table
            attrs["object_uuid"] = object_uuid
        if not attrs.get("db_table") or not attrs.get("object_uuid"):
            raise serializers.ValidationError(
                "Entweder target_reference oder db_table + object_uuid angeben."
            )
        if not attrs.get("name"):
            raise serializers.ValidationError({"name": "Ein Tag braucht einen Namen."})
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Tag:
        """Restore an existing soft-deleted tag instead of violating its unique key."""
        existing = Tag.all_objects.filter(
            db_table=validated_data["db_table"],
            object_uuid=validated_data["object_uuid"],
            name=validated_data["name"],
        ).first()
        if existing is not None:
            if existing.is_deleted:
                existing.restore()
            return existing
        return super().create(validated_data)


@register_serializer
class SettingSerializer(BaseSerializer):
    """Secrets are never returned – only whether they are set."""

    is_set = serializers.SerializerMethodField()
    value = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Setting
        fields = BaseSerializer.BASE_FIELDS + (
            "key",
            "value",
            "value_type",
            "is_secret",
            "description",
            "is_set",
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS + ("is_secret",)

    def get_is_set(self, obj: Setting) -> bool:
        return obj.value not in (None, "")

    def to_representation(self, instance: Setting) -> dict[str, Any]:
        data = super().to_representation(instance)
        if instance.is_secret:
            data["value"] = None
        return data


@register_serializer
class FileSerializer(BaseSerializer):
    download_url = serializers.CharField(read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True, default="")

    class Meta:
        model = File
        fields = BaseSerializer.BASE_FIELDS + (
            "file",
            "original_name",
            "content_type",
            "size",
            "purpose",
            "status",
            "account",
            "account_name",
            "stats",
            "error_message",
            "processed_at",
            "download_url",
        )
        read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS + (
            "content_type",
            "size",
            "status",
            "stats",
            "error_message",
            "processed_at",
            "download_url",
        )
        extra_kwargs = {"file": {"write_only": False}}

    def create(self, validated_data: dict[str, Any]) -> File:
        upload = validated_data.get("file")
        if upload is not None:
            validated_data.setdefault("original_name", getattr(upload, "name", ""))
            validated_data.setdefault("content_type", getattr(upload, "content_type", "") or "")
            validated_data.setdefault("size", getattr(upload, "size", 0) or 0)
        return super().create(validated_data)
