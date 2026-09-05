from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from base.models import File, Household
from finance.models import Account, Transaction
from finance.services.seed import ensure_default_categories, get_fallback_category
from imports.services.backup import build_backup, restore_backup
from imports.services.csv_parser import ParsedRow
from imports.tasks import analyse_import_file, commit_import
from users.models import User


class ImportWorkflowTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="test@example.com", password="sicheres-passwort", name="Test"
        )
        self.household = Household.objects.create(name="Zuhause", created_by=self.user)
        self.user.households.add(self.household)
        self.user.current_household = self.household
        self.user.save(update_fields=["current_household"])
        self.account = Account.objects.create(
            name="Giro", household=self.household, created_by=self.user
        )
        self.savings = Account.objects.create(
            name="Tagesgeld", household=self.household, created_by=self.user
        )
        ensure_default_categories(user=self.user, household=self.household)
        self.fallback = get_fallback_category(household=self.household)

    def test_analysis_is_non_mutating_and_commit_pairs_internal_transfer(self) -> None:
        duplicate = ParsedRow(
            booking_date=date(2026, 8, 1),
            amount=Decimal("-10.00"),
            counterparty="Laden",
            purpose="Einkauf",
        )
        Transaction.objects.create(
            name="Schon da",
            account=self.account,
            category=self.fallback,
            amount=duplicate.amount,
            booking_date=duplicate.booking_date,
            state=Transaction.State.REALITY,
            source=Transaction.Source.IMPORT,
            counterparty=duplicate.counterparty,
            purpose=duplicate.purpose,
            import_hash=duplicate.fingerprint(str(self.account.pk)),
        )
        counterpart = Transaction.objects.create(
            name="Umbuchung Eingang",
            account=self.savings,
            category=self.fallback,
            amount=Decimal("100.00"),
            booking_date=date(2026, 8, 2),
            state=Transaction.State.REALITY,
        )
        upload = File.objects.create(
            name="bank.csv",
            original_name="bank.csv",
            file="uploads/bank.csv",
            purpose=File.Purpose.TRANSACTION_IMPORT,
            account=self.account,
            household=self.household,
            created_by=self.user,
        )
        csv_content = (
            "Buchungstag;Beguenstigter;Verwendungszweck;Betrag\n"
            "01.08.2026;Laden;Einkauf;-10,00\n"
            "02.08.2026;Eigenkonto;Umbuchung;-100,00\n"
        ).encode()

        before = Transaction.objects.count()
        with patch("imports.tasks._read_file", return_value=csv_content):
            result = analyse_import_file.run(str(upload.pk))
        upload.refresh_from_db()

        self.assertEqual(Transaction.objects.count(), before)
        self.assertEqual(upload.status, File.Status.READY)
        self.assertEqual(result["new"], 1)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(result["internal_transfers"], 1)

        committed = commit_import.run(str(upload.pk), str(self.user.pk))
        upload.refresh_from_db()
        counterpart.refresh_from_db()
        imported = Transaction.objects.get(import_file=upload)

        self.assertEqual(committed["imported"], 1)
        self.assertEqual(upload.status, File.Status.COMPLETED)
        self.assertTrue(imported.is_internal_transfer)
        self.assertEqual(imported.transfer_pair, counterpart)
        self.assertTrue(counterpart.is_internal_transfer)
        self.assertEqual(counterpart.transfer_pair, imported)
        self.assertEqual(imported.category.slug, "umbuchung")

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_fin_roundtrip_replaces_household_data(self) -> None:
        source_file = File.objects.create(
            name="Beleg",
            original_name="beleg.txt",
            file=SimpleUploadedFile("beleg.txt", b"Originaldatei"),
            content_type="text/plain",
            size=13,
            purpose=File.Purpose.DOCUMENT,
            household=self.household,
            created_by=self.user,
        )
        original = Transaction.objects.create(
            name="Original",
            account=self.account,
            category=self.fallback,
            amount=Decimal("42.50"),
            booking_date=date(2026, 7, 1),
            state=Transaction.State.REALITY,
            import_file=source_file,
        )
        original_id = original.pk
        content = build_backup(self.household).getvalue()
        original.delete(hard=True)
        Transaction.objects.create(
            name="Soll verschwinden",
            account=self.account,
            category=self.fallback,
            amount=Decimal("-1.00"),
            booking_date=date(2026, 7, 2),
            state=Transaction.State.REALITY,
        )

        counts = restore_backup(content, household=self.household, user=self.user)

        self.assertEqual(counts["transactions"], 1)
        restored = Transaction.objects.get()
        self.assertEqual(restored.pk, original_id)
        self.assertEqual(restored.name, "Original")
        self.assertEqual(restored.amount, Decimal("42.50"))
        self.assertIsNotNone(restored.import_file)
        with restored.import_file.file.open("rb") as handle:
            self.assertEqual(handle.read(), b"Originaldatei")
