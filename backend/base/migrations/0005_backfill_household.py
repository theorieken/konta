from django.db import migrations


def backfill_household(apps, schema_editor):
    """Attach legacy single-household data before household scoping is enforced."""
    Household = apps.get_model("base", "Household")
    File = apps.get_model("base", "File")
    Setting = apps.get_model("base", "Setting")
    Tag = apps.get_model("base", "Tag")
    Account = apps.get_model("finance", "Account")
    Category = apps.get_model("finance", "Category")
    User = apps.get_model("users", "User")

    household_name = "Mein Haushalt"
    legacy_name = Setting.objects.filter(key="household_name").first()
    if legacy_name and isinstance(legacy_name.value, str) and legacy_name.value.strip():
        household_name = legacy_name.value.strip()

    household = Household.objects.order_by("created_at").first()
    if household is None:
        household = Household.objects.create(name=household_name)

    for user in User.objects.all():
        user.households.add(household)
        if user.current_household_id is None:
            user.current_household_id = household.id
            user.save(update_fields=["current_household"])

    for model in (Account, Category, Setting, File, Tag):
        model.objects.filter(household__isnull=True).update(household=household)


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0004_file_processed_data_alter_file_purpose_and_more"),
        ("finance", "0003_account_household_category_household_and_more"),
        ("users", "0003_user_current_household_user_households"),
    ]

    operations = [migrations.RunPython(backfill_household, migrations.RunPython.noop)]
