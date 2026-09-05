from django.apps import AppConfig


class BaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "base"
    verbose_name = "Basis"

    def ready(self) -> None:
        # Populate the serializer registry used by the generic object API.
        from base.serializers import load_all_serializers

        load_all_serializers()
