from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "name", "is_staff", "is_active", "created_at")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "name", "first_name", "last_name")
    readonly_fields = ("id", "created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profil", {"fields": ("name", "first_name", "last_name", "color", "notes")}),
        ("Rechte", {"fields": ("is_active", "is_staff", "is_superuser", "groups",
                               "user_permissions")}),
        ("Meta", {"fields": ("id", "is_onboarded", "created_at", "updated_at", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )
