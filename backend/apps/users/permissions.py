from rest_framework.permissions import BasePermission, SAFE_METHODS

from .access import user_has_permission


class HasCompanyAccessPermission(BasePermission):
    """Apply view/manage permission codes declared by a DRF view.

    Views opt in with ``access_view_permission`` and
    ``access_manage_permission``.  Admin override and legacy-safe behaviour are
    centralised in ``user_has_permission``.
    """

    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        code = (
            getattr(view, 'access_view_permission', None)
            if request.method in SAFE_METHODS
            else getattr(view, 'access_manage_permission', None)
        )
        return not code or user_has_permission(request.user, code)
