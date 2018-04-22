
from djingles.exceptions import LoginRequired, PermissionRequired
from django.core.exceptions import PermissionDenied


__all__ = ['PermissionRequiredMixin', 'PrivilegeRequiredMixin', 'LoginRequiredMixin',
           'StaffRequiredMixin', 'SuperUserRequiredMixin', 'OwnerRequiredMixin']


class PermissionRequiredMixin(object):

    def get_permission_url(cls, user):
        raise NotImplementedError

    def get_user(self):
        user = super(PermissionRequiredMixin, self).get_user()
        url = self.get_permission_url()
        if url is not None:
            raise PermissionRequired(url)
        return user


class LoginRequiredMixin(object):

    def get_user(self):
        user = super(LoginRequiredMixin, self).get_user()
        if not user.is_authenticated():
            raise LoginRequired
        return user


class OwnerRequiredMixin(LoginRequiredMixin):

    def get_target(self):
        obj = super(OwnerRequiredMixin, self).get_target()
        if not self.user.is_superuser and obj.owner != self.user:
            raise PermissionDenied
        return obj


class PrivilegeRequiredMixin(LoginRequiredMixin):
    
    def get_user(self):
        user = super(PrivilegeRequiredMixin, self).get_user()
        if not self.has_privileges(user):
            raise PermissionDenied
        return user

    def has_privileges(self, user):
        raise NotImplementedError


class StaffRequiredMixin(PrivilegeRequiredMixin):

    def has_privileges(self, user):
        return user.is_staff


class SuperUserRequiredMixin(PrivilegeRequiredMixin):

    def has_privileges(self, user):
        return user.is_superuser

