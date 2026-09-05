"""
Base view layer.

`BaseViewSet` is the parent of every model viewset: consistent permissions,
`created_by` handling, soft deletion, tag endpoints, prefetched tags and a
WebSocket broadcast for every mutation.

`ObjectViewSet` is the generic entry point the frontend uses for the object
drawer and the `/objects/{reference}` page.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from base.events import broadcast_object
from base.households import active_household, belongs_to_household, scope_queryset
from base.models import BaseModel, File, Household, Setting, Tag
from base.permissions import IsAuthenticatedHousehold
from base.queue import enqueue
from base.registry import (
    get_model_for_table,
    model_registry,
    resolve_reference,
    split_reference,
)
from base.serializers import (
    SERIALIZER_REGISTRY,
    FileSerializer,
    HouseholdSerializer,
    SettingSerializer,
    TagSerializer,
    TagWriteSerializer,
    load_all_serializers,
)
from base.settings_registry import DEFINITIONS


def build_tag_map(objects: list[BaseModel]) -> dict[str, list[Tag]]:
    """One query for the tags of a whole page of objects."""
    if not objects:
        return {}
    by_table: dict[str, list[Any]] = defaultdict(list)
    for obj in objects:
        by_table[obj._meta.db_table].append(obj.pk)

    tag_map: dict[str, list[Tag]] = defaultdict(list)
    for db_table, ids in by_table.items():
        for tag in Tag.objects.filter(db_table=db_table, object_uuid__in=ids):
            tag_map[f"{db_table}-{tag.object_uuid}"].append(tag)
    return tag_map


class BaseViewSet(viewsets.ModelViewSet):
    """CRUD for a BaseModel subclass."""

    permission_classes = [IsAuthenticatedHousehold]
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_queryset(
            queryset, active_household(self.request.user), user=self.request.user
        )

    # -- context --------------------------------------------------------------
    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        if getattr(self, "_tag_map", None) is not None:
            context["tag_map"] = self._tag_map
        return context

    def list(self, request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        objects = list(page) if page is not None else list(queryset)
        self._tag_map = build_tag_map(objects)
        serializer = self.get_serializer(objects, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    # -- mutations ------------------------------------------------------------
    def perform_create(self, serializer) -> None:
        instance = serializer.save()
        broadcast_object(instance, "created")

    def perform_update(self, serializer) -> None:
        instance = serializer.save()
        broadcast_object(instance, "updated")

    def perform_destroy(self, instance) -> None:
        reference = instance.object_reference
        instance.delete()  # soft delete
        broadcast_object(instance, "deleted", {"object_reference": reference})

    # -- tags -----------------------------------------------------------------
    @action(detail=True, methods=["get", "post"], url_path="tags")
    def tags(self, request, *args, **kwargs) -> Response:
        obj = self.get_object()
        if request.method == "GET":
            return Response(TagSerializer(obj.tags, many=True).data)

        name = (request.data.get("name") or "").strip()
        if not name:
            raise ValidationError({"name": "Ein Tag braucht einen Namen."})
        tag = obj.add_tag(name, request.data.get("color", ""), created_by=request.user)
        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"tags/(?P<tag_name>[^/]+)")
    def remove_tag(self, request, tag_name: str, *args, **kwargs) -> Response:
        obj = self.get_object()
        obj.remove_tag(tag_name)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, *args, **kwargs) -> Response:
        model = self.get_queryset().model
        queryset = scope_queryset(
            model.all_objects,
            active_household(request.user),
            user=request.user,
        )
        instance = queryset.filter(pk=kwargs.get("pk")).first()
        if instance is None:
            raise NotFound("Objekt nicht gefunden.")
        instance.restore()
        broadcast_object(instance, "updated")
        return Response(self.get_serializer(instance).data)


# -----------------------------------------------------------------------------
# Generic object access
# -----------------------------------------------------------------------------
class ObjectView(APIView):
    """
    `/api/objects/{db_table}-{uuid}/`

    Resolves any object reference to its canonical serializer. Powers the
    object drawer and the `/objects/[reference]` page in the frontend.
    """

    permission_classes = [IsAuthenticatedHousehold]

    def _resolve(self, reference: str) -> BaseModel:
        load_all_serializers()
        try:
            obj = resolve_reference(reference)
            if not belongs_to_household(obj, active_household(self.request.user)):
                raise NotFound(f"Objekt {reference} nicht gefunden.")
            return obj
        except DjangoValidationError as exc:
            raise ValidationError({"reference": exc.messages}) from exc
        except Exception as exc:  # DoesNotExist
            raise NotFound(f"Objekt {reference} nicht gefunden.") from exc

    def _serializer_class(self, obj: BaseModel):
        load_all_serializers()
        serializer_class = SERIALIZER_REGISTRY.get(obj._meta.db_table)
        if serializer_class is None:
            raise NotFound(f"Für {obj._meta.db_table} ist kein Serializer registriert.")
        return serializer_class

    def get(self, request, reference: str) -> Response:
        obj = self._resolve(reference)
        serializer_class = self._serializer_class(obj)
        return Response(serializer_class(obj, context={"request": request}).data)

    def patch(self, request, reference: str) -> Response:
        obj = self._resolve(reference)
        serializer_class = self._serializer_class(obj)
        serializer = serializer_class(
            obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        broadcast_object(instance, "updated")
        return Response(serializer.data)

    def delete(self, request, reference: str) -> Response:
        obj = self._resolve(reference)
        obj.delete()
        broadcast_object(obj, "deleted", {"object_reference": reference})
        return Response(status=status.HTTP_204_NO_CONTENT)


class ObjectBatchView(APIView):
    """`/api/objects/?references=a,b,c` – used to hydrate lists of references."""

    permission_classes = [IsAuthenticatedHousehold]

    def get(self, request) -> Response:
        load_all_serializers()
        raw = request.query_params.get("references", "")
        references = [ref.strip() for ref in raw.split(",") if ref.strip()]
        if not references:
            raise ValidationError({"references": "Bitte mindestens eine Referenz angeben."})

        results: list[dict[str, Any]] = []
        missing: list[str] = []
        for reference in references[:200]:
            try:
                obj = resolve_reference(reference)
            except Exception:
                missing.append(reference)
                continue
            if not belongs_to_household(obj, active_household(request.user)):
                missing.append(reference)
                continue
            serializer_class = SERIALIZER_REGISTRY.get(obj._meta.db_table)
            if serializer_class is None:
                missing.append(reference)
                continue
            results.append(serializer_class(obj, context={"request": request}).data)
        return Response({"results": results, "missing": missing})


class ObjectSchemaView(APIView):
    """
    `/api/objects/schema/` – what the frontend needs to render unknown models
    generically: table names, labels and where their collection lives.
    """

    permission_classes = [IsAuthenticatedHousehold]

    ENDPOINTS = {
        "base_tag": "/api/tags/",
        "base_setting": "/api/settings/",
        "base_file": "/api/files/",
        "base_household": "/api/households/",
        "users_user": "/api/users/",
        "finance_account": "/api/accounts/",
        "finance_category": "/api/categories/",
        "finance_transaction": "/api/transactions/",
        "finance_contract": "/api/contracts/",
        "finance_loan": "/api/loans/",
        "finance_job": "/api/jobs/",
    }

    def get(self, request) -> Response:
        load_all_serializers()
        models = []
        for db_table, model in sorted(model_registry().items()):
            models.append(
                {
                    "db_table": db_table,
                    "model": model.get_model_label(),
                    "verbose_name": str(model._meta.verbose_name),
                    "verbose_name_plural": str(model._meta.verbose_name_plural),
                    "endpoint": self.ENDPOINTS.get(db_table, ""),
                    "has_serializer": db_table in SERIALIZER_REGISTRY,
                }
            )
        return Response({"models": models})


# -----------------------------------------------------------------------------
# Concrete viewsets
# -----------------------------------------------------------------------------
class TagViewSet(BaseViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagWriteSerializer
    filterset_fields = ["db_table", "object_uuid", "name"]
    search_fields = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        reference = self.request.query_params.get("reference")
        if reference:
            db_table, object_uuid = split_reference(reference)
            get_model_for_table(db_table)
            queryset = queryset.filter(db_table=db_table, object_uuid=object_uuid)
        return queryset

    @action(detail=False, methods=["get"], url_path="names")
    def names(self, request) -> Response:
        """Distinct tag names for autocomplete."""
        names = (
            self.get_queryset().order_by("name").values_list("name", flat=True).distinct()
        )
        return Response({"results": list(names)})


class SettingViewSet(BaseViewSet):
    """
    Settings behave like a dictionary, so the collection endpoint also accepts
    `PUT /api/settings/bulk/` with `{"key": value, ...}`.
    """

    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    lookup_field = "key"
    lookup_value_regex = "[^/]+"
    filterset_fields = ["key", "value_type"]
    search_fields = ["key", "name", "description"]

    @action(detail=False, methods=["get"], url_path="definitions")
    def definitions(self, request) -> Response:
        """Every known setting plus its current value (secrets masked)."""
        household = active_household(request.user)
        stored = {row.key: row for row in Setting.objects.filter(household=household)}
        payload = []
        for definition in DEFINITIONS:
            row = stored.get(definition.key)
            entry = definition.as_dict()
            entry["value"] = (
                None
                if definition.is_secret
                else Setting.get(definition.key, household=household)
            )
            entry["is_set"] = bool(row and row.value not in (None, ""))
            entry["object_reference"] = row.object_reference if row else None
            payload.append(entry)
        return Response({"results": payload})

    @action(detail=False, methods=["put", "post"], url_path="bulk")
    def bulk(self, request) -> Response:
        """`{"openai_api_key": "sk-…", "prediction_horizon_months": 36}`"""
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Erwartet wird ein JSON-Objekt."})
        updated = []
        household = active_household(request.user)
        for key, value in request.data.items():
            row = Setting.set(key, value, user=request.user, household=household)
            updated.append(row.key)
            broadcast_object(row, "updated")
        return Response({"updated": updated})


class FileViewSet(BaseViewSet):
    queryset = File.objects.select_related("account").all()
    serializer_class = FileSerializer
    filterset_fields = ["purpose", "status", "account"]
    search_fields = ["name", "original_name"]

    def perform_create(self, serializer) -> None:
        instance = serializer.save()
        broadcast_object(instance, "created")
        if instance.purpose in (File.Purpose.TRANSACTION_IMPORT, File.Purpose.BACKUP_IMPORT):
            from imports.tasks import analyse_import_file

            enqueue(analyse_import_file, str(instance.pk))

    def perform_destroy(self, instance) -> None:
        if instance.transactions.exists():
            raise ValidationError(
                {"detail": "Diese Datei wird von importierten Transaktionen referenziert."}
            )
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="reprocess")
    def reprocess(self, request, pk: str | None = None) -> Response:
        """Run the CSV import for this file again."""
        from imports.tasks import analyse_import_file

        instance = self.get_object()
        instance.mark(File.Status.PENDING, stats={})
        instance.processed_data = {}
        instance.save(update_fields=["processed_data", "updated_at"])
        enqueue(analyse_import_file, str(instance.pk))
        return Response(self.get_serializer(instance).data)


class HouseholdViewSet(BaseViewSet):
    queryset = Household.objects.all()
    serializer_class = HouseholdSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer) -> None:
        instance = serializer.save(created_by=self.request.user)
        self.request.user.households.add(instance)
        from base.settings_registry import DEFINITIONS
        from finance.services.seed import ensure_default_categories

        for definition in DEFINITIONS:
            Setting.set(
                definition.key,
                definition.resolve_default(),
                user=self.request.user,
                household=instance,
            )
        ensure_default_categories(user=self.request.user, household=instance)
        broadcast_object(instance, "created")

    def perform_destroy(self, instance) -> None:
        if self.request.user.households.count() <= 1:
            raise ValidationError({"detail": "Der einzige Haushalt kann nicht gelöscht werden."})
        if self.request.user.current_household_id == instance.pk:
            raise ValidationError(
                {"detail": "Bitte zuerst zu einem anderen Haushalt wechseln."}
            )
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk: str | None = None) -> Response:
        household = self.get_object()
        request.user.current_household = household
        request.user.save(update_fields=["current_household", "updated_at"])
        return Response(self.get_serializer(household).data)


# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request) -> Response:
    """Used by the docker healthcheck and by deploy.sh."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database_ok = True
    except Exception:
        database_ok = False
    return Response(
        {"status": "ok" if database_ok else "degraded", "database": database_ok},
        status=status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
