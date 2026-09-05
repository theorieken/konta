"""Household selection and queryset scoping shared by every API."""

from __future__ import annotations

from django.db.models import QuerySet


def active_household(user):
    """Return the user's selected household, repairing legacy users once."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    current = getattr(user, "current_household", None)
    if current is not None and user.households.filter(pk=current.pk).exists():
        return current
    household = user.households.first()
    if household is None:
        from base.models import Household

        household = Household.objects.create(name="Mein Haushalt", created_by=user)
        user.households.add(household)
    user.current_household = household
    user.save(update_fields=["current_household", "updated_at"])
    return household


def object_household(obj):
    """Resolve direct and account-derived household ownership."""
    direct = getattr(obj, "household", None)
    if direct is not None:
        return direct
    account = getattr(obj, "account", None)
    if account is not None:
        return getattr(account, "household", None)
    return None


def belongs_to_household(obj, household) -> bool:
    from base.models import Household

    if isinstance(obj, Household):
        return obj.pk == getattr(household, "pk", None)
    owner = object_household(obj)
    if owner is not None:
        return owner.pk == getattr(household, "pk", None)
    memberships = getattr(obj, "households", None)
    return bool(memberships and memberships.filter(pk=getattr(household, "pk", None)).exists())


def scope_queryset(queryset: QuerySet, household, *, user=None) -> QuerySet:
    """Apply the appropriate household relation without per-view repetition."""
    model = queryset.model
    field_names = {field.name for field in model._meta.get_fields()}
    if model._meta.label_lower == "base.household":
        return queryset.filter(members=user) if user is not None else queryset.none()
    if model._meta.label_lower == "users.user":
        return queryset.filter(households=household).distinct()
    if "household" in field_names:
        return queryset.filter(household=household)
    if "account" in field_names:
        return queryset.filter(account__household=household)
    return queryset.none()
