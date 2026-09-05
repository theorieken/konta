from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthenticatedHousehold(BasePermission):
    """
    Everyone who is logged in belongs to the same household and may read and
    write everything. Ownership is tracked via `created_by` for the audit
    trail, not as an access boundary – that is a deliberate product decision
    for a shared household plan.
    """

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsSelfOrStaff(BasePermission):
    """Users may edit their own profile; staff may edit everyone."""

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff or obj.pk == request.user.pk
