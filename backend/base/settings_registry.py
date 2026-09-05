"""
Typed definitions for every key/value setting.

Adding a setting means adding one entry here – the API (`/api/settings/`), the
seed command and the frontend settings page all read from this registry, so
there is exactly one place to touch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from django.conf import settings as django_settings

# --- keys --------------------------------------------------------------------
OPENAI_API_KEY = "openai_api_key"
OPENAI_MODEL = "openai_model"
OPENAI_BASE_URL = "openai_base_url"
OPENAI_BATCH_SIZE = "openai_batch_size"
AUTO_CLASSIFY = "auto_classify_imports"

PREDICTION_HORIZON_MONTHS = "prediction_horizon_months"
DASHBOARD_RANGE_FROM = "dashboard_range_from"
DASHBOARD_RANGE_UNTIL = "dashboard_range_until"
SAVINGS_GOAL = "savings_goal"
SAVINGS_GOAL_DATE = "savings_goal_date"
HOUSEHOLD_NAME = "household_name"
CURRENCY = "currency"
MATCH_TOLERANCE_DAYS = "match_tolerance_days"
MATCH_TOLERANCE_PERCENT = "match_tolerance_percent"

EMAIL_HOST = "email_host"
EMAIL_PORT = "email_port"
EMAIL_HOST_USER = "email_host_user"
EMAIL_HOST_PASSWORD = "email_host_password"
EMAIL_USE_TLS = "email_use_tls"
EMAIL_FROM_ADDRESS = "email_from_address"

# Model choices offered in the settings UI. Free text is allowed as well, so
# any OpenAI compatible gateway can be used by typing its model name.
OPENAI_MODEL_CHOICES = [
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o-mini",
    "gpt-4o",
    "o4-mini",
]


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    label: str
    value_type: str = "string"
    default: Any = None
    default_factory: Callable[[], Any] | None = None
    is_secret: bool = False
    description: str = ""
    group: str = "Allgemein"
    choices: list[str] = field(default_factory=list)

    def resolve_default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        return self.default

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value_type": self.value_type,
            "default": self.resolve_default() if not self.is_secret else None,
            "is_secret": self.is_secret,
            "description": self.description,
            "group": self.group,
            "choices": self.choices,
        }


DEFINITIONS: list[SettingDefinition] = [
    # --- Haushalt ------------------------------------------------------------
    SettingDefinition(
        key=CURRENCY,
        label="Währung",
        default_factory=lambda: getattr(django_settings, "DEFAULT_CURRENCY", "EUR"),
        description="ISO-Code der Währung, z. B. EUR.",
        group="Haushalt",
    ),
    # --- Planung -------------------------------------------------------------
    SettingDefinition(
        key=PREDICTION_HORIZON_MONTHS,
        label="Prognosehorizont (Monate)",
        value_type="number",
        default_factory=lambda: getattr(django_settings, "PREDICTION_HORIZON_MONTHS", 24),
        description="Wie weit in die Zukunft geplante Transaktionen erzeugt werden.",
        group="Planung",
    ),
    SettingDefinition(
        key=SAVINGS_GOAL,
        label="Sparziel",
        value_type="number",
        default=0,
        description="Zielbetrag, der bis zum Zielmonat erreicht werden soll.",
        group="Planung",
    ),
    SettingDefinition(
        key=SAVINGS_GOAL_DATE,
        label="Zielmonat",
        value_type="date",
        default=None,
        description="Monat, in dem das Sparziel erreicht sein soll.",
        group="Planung",
    ),
    SettingDefinition(
        key=DASHBOARD_RANGE_FROM,
        label="Dashboard: Zeitraum von",
        value_type="date",
        default=None,
        description="Leer lassen für „laufender Monat“.",
        group="Planung",
    ),
    SettingDefinition(
        key=DASHBOARD_RANGE_UNTIL,
        label="Dashboard: Zeitraum bis",
        value_type="date",
        default=None,
        description="Leer lassen für „Prognosehorizont“.",
        group="Planung",
    ),
    # --- Import --------------------------------------------------------------
    SettingDefinition(
        key=OPENAI_API_KEY,
        label="OpenAI API-Key",
        is_secret=True,
        default_factory=lambda: getattr(django_settings, "OPENAI_API_KEY", ""),
        description="Wird für die automatische Kategorisierung importierter Umsätze verwendet.",
        group="KI-Import",
    ),
    SettingDefinition(
        key=OPENAI_MODEL,
        label="OpenAI Modell",
        default_factory=lambda: getattr(django_settings, "OPENAI_MODEL", "gpt-4.1-mini"),
        description="Modell, das die Kategorien vorschlägt.",
        group="KI-Import",
        choices=OPENAI_MODEL_CHOICES,
    ),
    SettingDefinition(
        key=OPENAI_BASE_URL,
        label="OpenAI Base-URL",
        default_factory=lambda: getattr(django_settings, "OPENAI_BASE_URL", ""),
        description="Nur nötig für kompatible Gateways (Azure, LiteLLM, …).",
        group="KI-Import",
    ),
    SettingDefinition(
        key=OPENAI_BATCH_SIZE,
        label="Batch-Größe",
        value_type="number",
        default_factory=lambda: getattr(django_settings, "OPENAI_BATCH_SIZE", 25),
        description="Wie viele Transaktionen pro Anfrage klassifiziert werden.",
        group="KI-Import",
    ),
    SettingDefinition(
        key=AUTO_CLASSIFY,
        label="Automatisch kategorisieren",
        value_type="boolean",
        default=True,
        description="Neue Importe direkt durch die KI kategorisieren lassen.",
        group="KI-Import",
    ),
    SettingDefinition(
        key=MATCH_TOLERANCE_DAYS,
        label="Abgleich: Tage Toleranz",
        value_type="number",
        default=7,
        description="Wie weit Datum einer geplanten und einer echten Buchung abweichen darf.",
        group="KI-Import",
    ),
    SettingDefinition(
        key=MATCH_TOLERANCE_PERCENT,
        label="Abgleich: Betrag Toleranz (%)",
        value_type="number",
        default=15,
        description="Erlaubte prozentuale Abweichung beim Betrag.",
        group="KI-Import",
    ),
    # --- E-Mail --------------------------------------------------------------
    SettingDefinition(
        key=EMAIL_HOST,
        label="SMTP-Server",
        default_factory=lambda: getattr(django_settings, "EMAIL_HOST", ""),
        description="Leer lassen, um E-Mails lokal nur im Backend-Log auszugeben.",
        group="E-Mail",
    ),
    SettingDefinition(
        key=EMAIL_PORT,
        label="SMTP-Port",
        value_type="number",
        default_factory=lambda: getattr(django_settings, "EMAIL_PORT", 587),
        description="Üblicherweise 587 für STARTTLS.",
        group="E-Mail",
    ),
    SettingDefinition(
        key=EMAIL_HOST_USER,
        label="SMTP-Benutzer",
        default_factory=lambda: getattr(django_settings, "EMAIL_HOST_USER", ""),
        description="Benutzername für den E-Mail-Server.",
        group="E-Mail",
    ),
    SettingDefinition(
        key=EMAIL_HOST_PASSWORD,
        label="SMTP-Passwort",
        is_secret=True,
        default_factory=lambda: getattr(django_settings, "EMAIL_HOST_PASSWORD", ""),
        description="Wird nicht über die API zurückgegeben.",
        group="E-Mail",
    ),
    SettingDefinition(
        key=EMAIL_USE_TLS,
        label="STARTTLS verwenden",
        value_type="boolean",
        default_factory=lambda: getattr(django_settings, "EMAIL_USE_TLS", True),
        description="Verschlüsselt die Verbindung zum SMTP-Server.",
        group="E-Mail",
    ),
    SettingDefinition(
        key=EMAIL_FROM_ADDRESS,
        label="Absenderadresse",
        default_factory=lambda: getattr(
            django_settings, "DEFAULT_FROM_EMAIL", "finanzplanung@localhost"
        ),
        description="Adresse, die als Absender der System-E-Mails erscheint.",
        group="E-Mail",
    ),
]

SETTING_DEFINITIONS: dict[str, SettingDefinition] = {d.key: d for d in DEFINITIONS}
