from urllib.parse import urljoin
from django.utils.formats import localize
from django.utils import timezone
from .base import Formatter


__all__ = ['ChoiceFormatter', 'FileFormatter', 'ImageFormatter', 'CallableFormatter',
           "DecimalFormatter", "Formatter", 'LinkFormatter', 'ExternalLinkFormatter',
           "DateFormatter", "DateTimeFormatter",
           "TimeFormatter", "PhoneFormatter", "EmailFormatter", "IntegerFormatter"]


class ChoiceFormatter(Formatter):

    def format(self, value, name, source):
        parts = name.split("__")
        tail = parts.pop()
        while parts:
            item = parts.pop(0)
            source = getattr(source, item)
        method = getattr(source, "get_%s_display" % tail, None)
        return method() if method is not None else None


class FileFormatter(Formatter):

    def format(self, value, name, source):
        if not value:
            return ""
        from django.conf import settings
        obj = value
        url = urljoin(settings.MEDIA_URL, obj.url)
        name = obj.name
        tag = "<a href='%s' target='_blank'>%s</a>" % (url, name)
        return tag


class ImageFormatter(Formatter):

    def __init__(self, **kwargs):
        self.width = kwargs.pop("width", 48)
        self.height = kwargs.pop("height", 48)
        kwargs.setdefault("variants", "detail")
        super(ImageFormatter, self).__init__(**kwargs)

    def format(self, value, name, source):
        if not value:
            return ""
        url = value.url
        tag = "<img src='%s' width='%s' height='%s' >" % (url, self.width, self.height)
        return tag


class DateTimeFormatter(Formatter):

    def format(self, value, name, source):
        if value:
            if timezone.is_naive(value):
                value = timezone.make_aware(value)
            value = timezone.localtime(value)
        return localize(value)


class DateFormatter(Formatter):

    def format(self, value, name, source):
        return localize(value)


class TimeFormatter(Formatter):

    def format(self, value, name, source):
        return localize(value)


class DecimalFormatter(Formatter):

    def __init__(self, **kwargs):
        self.decimal_places=  kwargs.pop("decimal_places", 2)
        super(DecimalFormatter, self).__init__(**kwargs)

    def format(self, value, name, source):
        template = "%%.%df" % self.decimal_places
        return template % value


class IntegerFormatter(Formatter):

    def format(self, value, name, source):
        return value


class CallableFormatter(Formatter):
    def __init__(self, func, **kwargs):
        self.func = func
        super(CallableFormatter, self).__init__(**kwargs)

    def format(self, value, name, source):
        return self.func(value)


class EmailFormatter(Formatter):

    def format(self, value, name, source):
        return "<a href='mailto:%s' > %s </a>" % (value, value)


class PhoneFormatter(Formatter):

    def format(self, value, name, source):
        return "<a href='tel:%s'> %s </a>" % (value, value)


class ExternalLinkFormatter(Formatter):

    def format(self, value, name, source):
        url = self.url
        if callable(url):
            url = url(value)
        if not url:
            return value
        return "<a href='%s' target='_blank'> %s </a>" % (url, value)


class LinkFormatter(Formatter):

    def format(self, value, name, source):
        url = self.url
        if callable(url):
            url = url(value)
        if not url:
            return value
        return "<a href='%s' > %s </a>" % (url, value)