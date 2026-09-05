"""
Base models shared by every app.

`BaseModel` is the abstract parent of *all* concrete models in this project.
It gives every object a UUID primary key, a human readable `name`, audit
fields (`created_at`, `updated_at`, `created_by`), soft deletion and – most
importantly – an `object_reference` of the form ``{db_table}-{uuid}``.
That reference is the single addressing scheme used by the generic
`/api/objects/{reference}/` endpoint, by tags and by the frontend router.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone


class BaseQuerySet(models.QuerySet):
    """Queryset that knows about soft deletion."""

    def alive(self) -> "BaseQuerySet":
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> "BaseQuerySet":
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        """Soft delete the whole queryset."""
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class BaseManager(models.Manager.from_queryset(BaseQuerySet)):
    """Default manager – hides soft deleted rows."""

    def get_queryset(self) -> BaseQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager.from_queryset(BaseQuerySet)):
    """Escape hatch that also returns soft deleted rows."""


class BaseModel(models.Model):
    """Abstract parent of every model in this project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Bezeichnung", max_length=255, blank=True, default="")
    notes = models.TextField("Notiz", blank=True, default="")

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Geändert am", auto_now=True)
    deleted_at = models.DateTimeField("Gelöscht am", null=True, blank=True, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Erstellt von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
    )

    objects = BaseManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        ordering = ("-created_at",)

    # -- identity -------------------------------------------------------------
    def __str__(self) -> str:
        return self.display_name

    @classmethod
    def get_db_table(cls) -> str:
        """The database table name – first half of every object reference."""
        return cls._meta.db_table

    @classmethod
    def get_model_label(cls) -> str:
        return f"{cls._meta.app_label}.{cls._meta.model_name}"

    @property
    def table_name(self) -> str:
        return self._meta.db_table

    @property
    def object_reference(self) -> str:
        """``{db_table}-{uuid}`` – stable, globally unique, URL safe."""
        return f"{self._meta.db_table}-{self.id}"

    @property
    def display_name(self) -> str:
        """Never empty – falls back to the model name plus a short id."""
        if self.name:
            return self.name
        return f"{self._meta.verbose_name} {str(self.id)[:8]}"

    # -- tags -----------------------------------------------------------------
    @property
    def tags(self):
        return Tag.objects.for_object(self)

    def add_tag(self, name: str, color: str = "", created_by=None) -> "Tag":
        from base.households import object_household

        tag, _ = Tag.objects.get_or_create(
            db_table=self._meta.db_table,
            object_uuid=self.id,
            name=name,
            defaults={
                "color": color,
                "created_by": created_by,
                "household": object_household(self),
            },
        )
        return tag

    def remove_tag(self, name: str) -> int:
        deleted, _ = Tag.all_objects.filter(
            db_table=self._meta.db_table, object_uuid=self.id, name=name
        ).hard_delete()
        return deleted

    # -- soft deletion --------------------------------------------------------
    def delete(self, using=None, keep_parents=False, hard: bool = False):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
        return (1, {self._meta.label: 1})

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    # -- serialisation helpers ------------------------------------------------
    def meta_payload(self) -> dict[str, Any]:
        """The `_meta` block every serializer embeds. See BaseSerializer."""
        return {
            "id": str(self.id),
            "object_reference": self.object_reference,
            "db_table": self._meta.db_table,
            "model": self.get_model_label(),
            "verbose_name": str(self._meta.verbose_name),
            "verbose_name_plural": str(self._meta.verbose_name_plural),
            "name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "is_deleted": self.is_deleted,
        }


class Household(BaseModel):
    """One independent financial plan shared by one or more users."""

    class Meta:
        verbose_name = "Haushalt"
        verbose_name_plural = "Haushalte"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.display_name


class TagQuerySet(BaseQuerySet):
    def for_object(self, obj) -> "TagQuerySet":
        return self.filter(db_table=obj._meta.db_table, object_uuid=obj.pk)

    def for_reference(self, reference: str) -> "TagQuerySet":
        from base.registry import split_reference

        db_table, object_uuid = split_reference(reference)
        return self.filter(db_table=db_table, object_uuid=object_uuid)


class TagManager(models.Manager.from_queryset(TagQuerySet)):
    def get_queryset(self) -> TagQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)


class Tag(BaseModel):
    """
    Generic label that can be attached to *any* object.

    We deliberately do not use Django's contenttypes framework – the pair
    (`db_table`, `object_uuid`) is exactly the object reference the rest of the
    system already speaks, which keeps the API and the frontend simple.
    """

    household = models.ForeignKey(
        Household,
        verbose_name="Haushalt",
        on_delete=models.CASCADE,
        related_name="tags",
        null=True,
        blank=True,
    )
    db_table = models.CharField("Tabelle", max_length=120, db_index=True)
    object_uuid = models.UUIDField("Objekt", db_index=True)
    color = models.CharField("Farbe", max_length=32, blank=True, default="")

    objects = TagManager()
    all_objects = models.Manager.from_queryset(TagQuerySet)()

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ("name",)
        indexes = [models.Index(fields=["db_table", "object_uuid"])]
        constraints = [
            models.UniqueConstraint(
                fields=["db_table", "object_uuid", "name"],
                name="unique_tag_per_object",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def target_reference(self) -> str:
        return f"{self.db_table}-{self.object_uuid}"


class Setting(BaseModel):
    """
    Key/value configuration store for the whole household.

    Reading always goes through `Setting.get(key)`, which falls back to the
    definition in `base.settings_registry` and finally to Django settings.
    """

    class ValueType(models.TextChoices):
        STRING = "string", "Text"
        NUMBER = "number", "Zahl"
        BOOLEAN = "boolean", "Ja/Nein"
        DATE = "date", "Datum"
        JSON = "json", "JSON"

    household = models.ForeignKey(
        Household,
        verbose_name="Haushalt",
        on_delete=models.CASCADE,
        related_name="settings",
        null=True,
        blank=True,
    )
    key = models.CharField("Schlüssel", max_length=120, db_index=True)
    value = models.JSONField("Wert", null=True, blank=True, default=None)
    value_type = models.CharField(
        "Typ", max_length=16, choices=ValueType.choices, default=ValueType.STRING
    )
    is_secret = models.BooleanField("Geheim", default=False)
    description = models.TextField("Beschreibung", blank=True, default="")

    class Meta:
        verbose_name = "Einstellung"
        verbose_name_plural = "Einstellungen"
        ordering = ("key",)
        constraints = [
            models.UniqueConstraint(
                fields=["household", "key"], name="unique_setting_per_household"
            )
        ]

    def __str__(self) -> str:
        return self.key

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.key
        super().save(*args, **kwargs)

    # -- convenience ----------------------------------------------------------
    @classmethod
    def get(cls, key: str, default: Any = None, *, household=None) -> Any:
        from base.settings_registry import SETTING_DEFINITIONS

        if household is None:
            household = Household.objects.first()
        row = cls.objects.filter(key=key, household=household).first()
        if row is not None and row.value not in (None, ""):
            return row.value
        definition = SETTING_DEFINITIONS.get(key)
        if definition is not None:
            return definition.resolve_default()
        return default

    @classmethod
    def set(cls, key: str, value: Any, user=None, *, household=None) -> "Setting":
        from base.settings_registry import SETTING_DEFINITIONS

        if household is None and user is not None:
            household = getattr(user, "current_household", None)
        if household is None:
            household = Household.objects.first()
        definition = SETTING_DEFINITIONS.get(key)
        defaults: dict[str, Any] = {"value": value, "household": household}
        if definition is not None:
            defaults.update(
                {
                    "name": definition.label,
                    "value_type": definition.value_type,
                    "is_secret": definition.is_secret,
                    "description": definition.description,
                }
            )
        if user is not None and getattr(user, "is_authenticated", False):
            defaults["created_by"] = user
        row, _ = cls.objects.update_or_create(
            household=household, key=key, defaults=defaults
        )
        return row


class File(BaseModel):
    """
    An uploaded file stored in MinIO.

    CSV bank statements are uploaded with `purpose = TRANSACTION_IMPORT`;
    the import pipeline in the `imports` app tracks its progress on this very
    row, which keeps the model count low and the UI simple.
    """

    class Purpose(models.TextChoices):
        TRANSACTION_IMPORT = "transaction_import", "Kontoumsätze (CSV)"
        BACKUP_IMPORT = "backup_import", "Finanz-Sicherung (.fin)"
        DOCUMENT = "document", "Dokument"
        OTHER = "other", "Sonstiges"

    class Status(models.TextChoices):
        PENDING = "pending", "Wartet"
        PROCESSING = "processing", "Wird verarbeitet"
        READY = "ready", "Bereit zum Import"
        COMPLETED = "completed", "Abgeschlossen"
        FAILED = "failed", "Fehlgeschlagen"

    household = models.ForeignKey(
        Household,
        verbose_name="Haushalt",
        on_delete=models.CASCADE,
        related_name="files",
        null=True,
        blank=True,
    )
    file = models.FileField("Datei", upload_to="uploads/%Y/%m/")
    original_name = models.CharField("Dateiname", max_length=255, blank=True, default="")
    content_type = models.CharField("MIME-Typ", max_length=120, blank=True, default="")
    size = models.BigIntegerField("Größe", default=0)

    purpose = models.CharField(
        "Zweck", max_length=32, choices=Purpose.choices, default=Purpose.DOCUMENT, db_index=True
    )
    status = models.CharField(
        "Status", max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    account = models.ForeignKey(
        "finance.Account",
        verbose_name="Konto",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="files",
        help_text="Konto, zu dem die importierten Umsätze gehören.",
    )

    stats = models.JSONField("Ergebnis", default=dict, blank=True)
    processed_data = models.JSONField(
        "Aufbereitete Daten",
        default=dict,
        blank=True,
        help_text="Serverseitige Importvorschau; wird nicht in Dateilisten ausgeliefert.",
    )
    error_message = models.TextField("Fehler", blank=True, default="")
    processed_at = models.DateTimeField("Verarbeitet am", null=True, blank=True)

    class Meta:
        verbose_name = "Datei"
        verbose_name_plural = "Dateien"
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.original_name or (self.file.name if self.file else "Datei")
        super().save(*args, **kwargs)

    @property
    def download_url(self) -> str:
        """Presigned URL rewritten to the browser reachable MinIO endpoint."""
        if not self.file:
            return ""
        try:
            url = self.file.url
        except Exception:  # storage not reachable – never break the API
            return ""
        internal = getattr(settings, "MINIO_ENDPOINT", "")
        public = getattr(settings, "MINIO_PUBLIC_ENDPOINT", "")
        if internal and public and url.startswith(internal):
            return public + url[len(internal):]
        return url

    def mark(self, status: str, *, error: str = "", stats: dict | None = None) -> None:
        self.status = status
        self.error_message = error
        if stats is not None:
            self.stats = stats
        if status in (self.Status.COMPLETED, self.Status.FAILED):
            self.processed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "stats", "processed_at", "updated_at"])
