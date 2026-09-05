import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0003_initial"),
        ("users", "0002_user_password_link_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Household",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True, default="", max_length=255, verbose_name="Bezeichnung"
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, default="", verbose_name="Notiz"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="Erstellt am"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Geändert am"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True, db_index=True, null=True, verbose_name="Gelöscht am"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Erstellt von",
                    ),
                ),
            ],
            options={
                "verbose_name": "Haushalt",
                "verbose_name_plural": "Haushalte",
                "ordering": ("name",),
            },
        ),
        migrations.AddField(
            model_name="file",
            name="household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="files",
                to="base.household",
                verbose_name="Haushalt",
            ),
        ),
        migrations.AddField(
            model_name="file",
            name="processed_data",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Serverseitige Importvorschau; wird nicht in Dateilisten ausgeliefert.",
                verbose_name="Aufbereitete Daten",
            ),
        ),
        migrations.AddField(
            model_name="setting",
            name="household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="settings",
                to="base.household",
                verbose_name="Haushalt",
            ),
        ),
        migrations.AddField(
            model_name="tag",
            name="household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tags",
                to="base.household",
                verbose_name="Haushalt",
            ),
        ),
        migrations.AlterField(
            model_name="file",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("transaction_import", "Kontoumsätze (CSV)"),
                    ("backup_import", "Finanz-Sicherung (.fin)"),
                    ("document", "Dokument"),
                    ("other", "Sonstiges"),
                ],
                db_index=True,
                default="document",
                max_length=32,
                verbose_name="Zweck",
            ),
        ),
        migrations.AlterField(
            model_name="file",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Wartet"),
                    ("processing", "Wird verarbeitet"),
                    ("ready", "Bereit zum Import"),
                    ("completed", "Abgeschlossen"),
                    ("failed", "Fehlgeschlagen"),
                ],
                db_index=True,
                default="pending",
                max_length=16,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="setting",
            name="key",
            field=models.CharField(
                db_index=True, max_length=120, verbose_name="Schlüssel"
            ),
        ),
        migrations.AddConstraint(
            model_name="setting",
            constraint=models.UniqueConstraint(
                fields=("household", "key"), name="unique_setting_per_household"
            ),
        ),
    ]
