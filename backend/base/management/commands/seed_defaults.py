"""
Idempotent bootstrap – runs on every backend start (see entrypoint.sh).

Creates the default categories, materialises the known settings and – when
`BOOTSTRAP_ADMIN_PASSWORD` is set – the first admin user. Never overwrites
anything a user has changed.
"""

from __future__ import annotations

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand

from base.models import Household, Setting
from base.settings_registry import DEFINITIONS


class Command(BaseCommand):
    help = "Legt Standardkategorien, Einstellungen und optional den ersten Benutzer an."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force-settings",
            action="store_true",
            help="Vorhandene Einstellungen auf die Standardwerte zurücksetzen.",
        )

    def handle(self, *args, **options) -> None:
        self._seed_settings(force=options.get("force_settings", False))
        self._seed_categories()
        self._seed_admin()

    # -- settings -------------------------------------------------------------
    def _seed_settings(self, force: bool) -> None:
        created = 0
        for household in Household.objects.all():
            for definition in DEFINITIONS:
                row = Setting.objects.filter(
                    household=household, key=definition.key
                ).first()
                if row is not None and not force:
                    continue
                default = definition.resolve_default()
                Setting.objects.update_or_create(
                    household=household,
                    key=definition.key,
                    defaults={
                        "name": definition.label,
                        "value": default,
                        "value_type": definition.value_type,
                        "is_secret": definition.is_secret,
                        "description": definition.description,
                    },
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Einstellungen: {created} angelegt/aktualisiert"))

    # -- categories -----------------------------------------------------------
    def _seed_categories(self) -> None:
        from finance.services.seed import ensure_default_categories

        created = sum(
            ensure_default_categories(household=household)
            for household in Household.objects.all()
        )
        self.stdout.write(self.style.SUCCESS(f"Kategorien: {created} neu angelegt"))

    # -- first user -----------------------------------------------------------
    def _seed_admin(self) -> None:
        from users.models import User

        password = (getattr(django_settings, "BOOTSTRAP_ADMIN_PASSWORD", "") or "").strip()
        if not password:
            if not User.objects.exists():
                self.stdout.write(
                    "Kein Benutzer vorhanden – die App startet mit dem Onboarding."
                )
            return
        if User.objects.exists():
            return

        email = getattr(django_settings, "BOOTSTRAP_ADMIN_EMAIL", "admin@localhost")
        user = User.objects.create_superuser(
            email=email,
            password=password,
            name=getattr(django_settings, "BOOTSTRAP_ADMIN_NAME", "Administrator"),
            is_onboarded=True,
        )
        household = Household.objects.first()
        if household is not None:
            user.households.add(household)
            user.current_household = household
            user.save(update_fields=["current_household", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"Administrator angelegt: {user.email}"))
