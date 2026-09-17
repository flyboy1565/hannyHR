from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class HRConsoleMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Gate the HR management console.

    Requires a logged-in user who is either a superuser or holds the
    ``employees.can_manage_hr`` permission. Non-HR staff are deliberately
    excluded from Django admin: normal HR accounts have ``is_staff=False``
    and are granted the permission via the "HR Staff" group instead.
    """

    login_url = 'hr:login'
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.has_perm('employees.can_manage_hr')