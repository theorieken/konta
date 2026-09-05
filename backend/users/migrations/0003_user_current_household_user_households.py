import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0004_file_processed_data_alter_file_purpose_and_more"),
        ("users", "0002_user_password_link_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="current_household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="active_members",
                to="base.household",
                verbose_name="Aktiver Haushalt",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="households",
            field=models.ManyToManyField(
                blank=True,
                related_name="members",
                to="base.household",
                verbose_name="Haushalte",
            ),
        ),
    ]
