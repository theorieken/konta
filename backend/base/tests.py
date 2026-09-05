from __future__ import annotations

from io import StringIO
from unittest.mock import ANY, call, patch

from django.core.management import call_command
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from base.management.commands.setup_periodic_tasks import SCHEDULE
from finance.services.seed import DEFAULT_CATEGORIES
from users.models import User


class ResetDataCommandTests(SimpleTestCase):
    @patch("base.management.commands.reset_data.Household.objects.create")
    @patch("base.management.commands.reset_data.call_command")
    @patch("builtins.input", return_value="RESET")
    def test_resets_and_rebuilds_operational_defaults(
        self, _input, nested_call, create_household
    ) -> None:
        output = StringIO()

        call_command("reset_data", stdout=output)

        create_household.assert_called_once_with(name="Mein Haushalt")
        self.assertEqual(
            nested_call.call_args_list,
            [
                call("flush", interactive=False, verbosity=0),
                call("seed_defaults", verbosity=1, stdout=ANY),
                call("setup_periodic_tasks", verbosity=1, stdout=ANY),
            ],
        )
        self.assertIn("Datenbank wurde zurückgesetzt", output.getvalue())

    @patch("base.management.commands.reset_data.call_command")
    @patch("builtins.input", return_value="nein")
    def test_aborts_without_exact_confirmation(self, _input, nested_call) -> None:
        output = StringIO()

        call_command("reset_data", stdout=output)

        nested_call.assert_not_called()
        self.assertIn("Abgebrochen", output.getvalue())


@override_settings(BOOTSTRAP_ADMIN_PASSWORD="")
class ResetDataIntegrationTests(TransactionTestCase):
    def test_flushes_users_and_restores_boot_defaults(self) -> None:
        from django_celery_beat.models import PeriodicTask
        from finance.models import Category

        User.objects.create_user(
            email="before-reset@example.test",
            password="Unusual!Password2026",
        )

        call_command("reset_data", yes=True, stdout=StringIO())

        self.assertFalse(User.objects.exists())
        self.assertEqual(Category.objects.count(), len(DEFAULT_CATEGORIES))
        self.assertEqual(PeriodicTask.objects.count(), len(SCHEDULE))
