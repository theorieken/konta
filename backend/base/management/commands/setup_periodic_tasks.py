"""
Register the celery beat schedule in the database.

Runs on every backend start so the schedule always matches the code. Tasks the
user disabled in the admin are left alone.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

# name, task, crontab(minute, hour, day_of_week), description
SCHEDULE: list[tuple[str, str, dict, str]] = [
    (
        "Geplante Transaktionen erzeugen",
        "finance.generate_planned_transactions",
        {"minute": "10", "hour": "3"},
        "Materialisiert Verträge, Kredite und Einkommen bis zum Prognosehorizont.",
    ),
    (
        "Buchungen mit Plan abgleichen",
        "finance.match_transactions",
        {"minute": "40", "hour": "3"},
        "Verknüpft importierte Buchungen mit den passenden geplanten Transaktionen.",
    ),
    (
        "Überfällige Planungen markieren",
        "finance.flag_overdue_planned",
        {"minute": "0", "hour": "4"},
        "Markiert geplante Transaktionen ohne echte Buchung zur Prüfung.",
    ),
    (
        "Hängengebliebene Importe aufräumen",
        "imports.cleanup_stale_imports",
        {"minute": "15"},
        "Setzt Importe, die länger als sechs Stunden laufen, auf „fehlgeschlagen“.",
    ),
    (
        "Abgelaufene Tokens entfernen",
        "base.prune_expired_tokens",
        {"minute": "30", "hour": "2"},
        "Räumt abgelaufene Auth-Tokens auf.",
    ),
    (
        "Papierkorb leeren",
        "base.purge_soft_deleted",
        {"minute": "0", "hour": "2", "day_of_week": "0"},
        "Löscht seit 90 Tagen gelöschte Objekte endgültig.",
    ),
]


class Command(BaseCommand):
    help = "Legt die periodischen Celery-Beat-Aufgaben an."

    def handle(self, *args, **options) -> None:
        for name, task, crontab, description in SCHEDULE:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=crontab.get("minute", "*"),
                hour=crontab.get("hour", "*"),
                day_of_week=crontab.get("day_of_week", "*"),
                day_of_month=crontab.get("day_of_month", "*"),
                month_of_year=crontab.get("month_of_year", "*"),
            )
            PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task": task,
                    "crontab": schedule,
                    "interval": None,
                    "description": description,
                    "args": json.dumps([]),
                    "kwargs": json.dumps({}),
                },
            )
        self.stdout.write(
            self.style.SUCCESS(f"Periodische Aufgaben registriert: {len(SCHEDULE)}")
        )
