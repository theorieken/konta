import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0004_file_processed_data_alter_file_purpose_and_more"),
        ("finance", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="accounts",
                to="base.household",
                verbose_name="Haushalt",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categories",
                to="base.household",
                verbose_name="Haushalt",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(max_length=80, verbose_name="Kürzel"),
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(
                fields=("household", "slug"),
                name="unique_category_slug_per_household",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="is_internal_transfer",
            field=models.BooleanField(
                db_index=True, default=False, verbose_name="Interne Umbuchung"
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="transfer_pair",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transfer_matches",
                to="finance.transaction",
                verbose_name="Gegenbuchung",
            ),
        ),
    ]
