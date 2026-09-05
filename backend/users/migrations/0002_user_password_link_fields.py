from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="password_link_expires_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Passwort-Link gültig bis"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="password_link_purpose",
            field=models.CharField(
                blank=True,
                choices=[
                    ("reset", "Passwort zurücksetzen"),
                    ("invitation", "Einladung"),
                ],
                default="",
                max_length=16,
                verbose_name="Passwort-Link Zweck",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="password_link_token_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=64,
                verbose_name="Passwort-Link (Hash)",
            ),
        ),
    ]
