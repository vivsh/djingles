
try:
    from django.utils import six
except ImportError:
    import six

from django.urls import reverse
from django.conf import settings
from django.shortcuts import resolve_url
from djingles import utils


__all__ = ["PermissionRequired", "LoginRequired", "PageExpired"]


class CommonHttpError(Exception):

    description = None

    def __init__(self, message=None):
        self.description = message if message is not None else self.description
        super(Exception, self).__init__(self.description)

    def to_json(self):
        messages = getattr(settings, "HTTP_ERROR_MESSAGES",{})
        class_name = self.__class__.__name__
        return {
            'message': messages.get(class_name, self.description),
            'type': class_name
        }


class PageExpired(CommonHttpError):
    status = 410
    description = "Content has moved"


class Redirect(CommonHttpError):
    permanent = False

    description = "Content has moved"

    def __init__(self, to, message=None, **kwargs):
        super(Redirect, self).__init__(message)
        self.to = to
        self.kwargs = kwargs

    def create_url(self, request):
        url = resolve_url(self.to, **self.kwargs)
        return url


class PermissionRequired(Redirect):
    status_code = 401
    description = "Permission Required"

    def __init__(self, url, message=None):
        super(PermissionRequired, self).__init__(url, message=message)

    def create_url(self, request):
        current_url = request.get_full_path()
        url = utils.url_query_update(self.to, {"next": current_url})
        return url


class LoginRequired(PermissionRequired):

    def __init__(self, message=None):
        url = reverse("login")
        super(LoginRequired, self).__init__(url, message=message)

    def create_url(self, request):
        current_url = request.get_full_path()
        url = utils.url_query_update(self.to, {"next": current_url})
        return url

