from django.contrib import admin

from base.models import File, Household, Setting, Tag


class BaseAdmin(admin.ModelAdmin):
    """Shared admin defaults: audit columns are read only."""

    readonly_fields = ("id", "created_at", "updated_at", "object_reference")
    list_per_page = 50

    @admin.display(description="Referenz")
    def object_reference(self, obj) -> str:
        return obj.object_reference


@admin.register(Household)
class HouseholdAdmin(BaseAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(BaseAdmin):
    list_display = ("name", "db_table", "object_uuid", "color", "created_at")
    list_filter = ("db_table",)
    search_fields = ("name", "object_uuid")


@admin.register(Setting)
class SettingAdmin(BaseAdmin):
    list_display = ("key", "value_type", "is_secret", "updated_at")
    list_filter = ("value_type", "is_secret")
    search_fields = ("key", "name", "description")


@admin.register(File)
class FileAdmin(BaseAdmin):
    list_display = ("name", "purpose", "status", "size", "account", "created_at")
    list_filter = ("purpose", "status")
    search_fields = ("name", "original_name")
