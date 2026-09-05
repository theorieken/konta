"""Create a login from the command line and add it to the household."""

from __future__ import annotations

import getpass

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

from base.models import Household
from finance.services.seed import ensure_default_categories
from users.models import User


class Command(BaseCommand):
    help = "Legt einen Benutzer an und fügt ihn dem Haushalt hinzu."

    def add_arguments(self, parser) -> None:
        parser.add_argument("email", help="E-Mail-Adresse für die Anmeldung.")
        parser.add_argument("--name", default="", help="Anzeigename des Benutzers.")
        parser.add_argument(
            "--password",
            help="Passwort (ohne diese Option wird es verdeckt abgefragt).",
        )
        parser.add_argument(
            "--admin",
            action="store_true",
            help="Benutzer als Administrator anlegen.",
        )

    def handle(self, *args, **options) -> None:
        email = User.objects.normalize_email(options["email"]).lower().strip()
        self._validate_email(email)
        if User.all_objects.filter(email=email).exists():
            raise CommandError(f"Ein Benutzer mit {email} existiert bereits.")

        password = options.get("password") or self._prompt_for_password()
        name = options["name"].strip()
        candidate = User(email=email, name=name)
        try:
            password_validation.validate_password(password, candidate)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        with transaction.atomic():
            create = (
                User.objects.create_superuser
                if options["admin"]
                else User.objects.create_user
            )
            user = create(
                email=email,
                password=password,
                name=name,
                is_onboarded=True,
            )
            household = Household.objects.first()
            if household is None:
                household = Household.objects.create(
                    name="Mein Haushalt", created_by=user
                )
            user.households.add(household)
            user.current_household = household
            user.save(update_fields=["current_household", "updated_at"])
            ensure_default_categories(user=user, household=household)

        role = "Administrator" if user.is_superuser else "Benutzer"
        self.stdout.write(self.style.SUCCESS(f"{role} angelegt: {user.email}"))

    @staticmethod
    def _validate_email(email: str) -> None:
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("Die E-Mail-Adresse ist ungültig.") from exc

    @staticmethod
    def _prompt_for_password() -> str:
        try:
            password = getpass.getpass("Passwort: ")
            confirmation = getpass.getpass("Passwort wiederholen: ")
        except (EOFError, KeyboardInterrupt) as exc:
            raise CommandError("Passworteingabe abgebrochen.") from exc
        if not password:
            raise CommandError("Das Passwort darf nicht leer sein.")
        if password != confirmation:
            raise CommandError("Die Passwörter stimmen nicht überein.")
        return password
