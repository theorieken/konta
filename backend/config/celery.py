"""Celery application. Beat schedules live in `base/management/commands/setup_periodic_tasks.py`."""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("finplan")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> str:  # pragma: no cover - manual debugging helper
    return f"request: {self.request!r}"
