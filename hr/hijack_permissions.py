def hijack_permission_check(*, hijacker, hijacked):
    """Custom permission check for django-hijack.

    - Superusers can hijack any non-superuser.
    - Users with can_hijack_users permission can hijack any non-superuser.
    - No one can hijack a superuser.
    """
    if not hijacked or not hijacked.is_active:
        return False

    if hijacked.is_superuser:
        return False

    if hijacker.is_superuser:
        return True

    return hijacker.has_perm('employees.can_hijack_users')
