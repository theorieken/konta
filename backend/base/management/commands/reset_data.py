"""Reset the database to the application's post-deployment state."""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand

from base.models import Household


class Command(BaseCommand):
    help = "Löscht alle Datenbankdaten und stellt Standarddaten und Zeitpläne wieder her."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Sicherheitsabfrage überspringen.",
        )

    def handle(self, *args, **options) -> None:
        if not options["yes"]:
            confirmation = input(
                "Alle Datenbankdaten werden unwiderruflich gelöscht. "
                "Zum Fortfahren RESET eingeben: "
            )
            if confirmation != "RESET":
                self.stdout.write(
                    self.style.WARNING("Abgebrochen. Es wurden keine Daten gelöscht.")
                )
                return

        verbosity = options["verbosity"]
        call_command("flush", interactive=False, verbosity=0)

        # These commands also run after a normal deployment. Reapplying them
        # leaves a reset installation in exactly the same operational state.
        Household.objects.create(name="Mein Haushalt")
        call_command("seed_defaults", verbosity=verbosity, stdout=self.stdout)
        call_command("setup_periodic_tasks", verbosity=verbosity, stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS("Datenbank wurde zurückgesetzt."))
