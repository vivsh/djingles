
from collections import OrderedDict
from django.core.exceptions import FieldDoesNotExist
from django.utils import six
from django.db import models
from .formatters import *
from .base import FormattedObject, FormattedTable
from django.conf import settings


__all__ = ['FormattedModel', 'FormattedModelTable', 'object_formatter_factory', 'table_formatter_factory']


FORMATTER_MAPPING = {
    models.DateTimeField: DateTimeFormatter,
    models.DateField: DateFormatter,
    models.TimeField: TimeFormatter,
    models.ImageField: ImageFormatter,
    models.FileField: FileFormatter,
    models.FloatField: DecimalFormatter,
    models.DecimalField: DecimalFormatter
}


FORMATTER_MAPPING.update(getattr(settings, 'FIELD_FORMATTERS', {}))


def get_formatter_for_field(factory, meta, field_map, field_name, options=None):
    parts = field_name.split("__")
    field_name = parts.pop(0)
    field = field_map.get(field_name)
    if not field:
        return Formatter()
    while parts and field.model:
        model = field.related_model
        item = parts.pop(0)
        field = model._meta.get_field(item)

    label = field.verbose_name.title()
    label = getattr(options, 'labels', {}).get(field.name, label)

    if hasattr(factory, "formatter_for_field"):
        result = factory.formatter_for_field(field)
        if result is not None:
            result.label = label
            return result
    try:
        result = getattr(field, 'get_formatter')()
        result.label = label
        return result
    except AttributeError:
        if field.choices:
            result = ChoiceFormatter(label=label)
        else:
            result = FORMATTER_MAPPING.get(field.__class__, Formatter)(label=label)
        return result


def get_formatters_for_model(factory, model_class, fields=None, exclude=None, options=None):
    meta = model_class._meta
    field_map = OrderedDict((f.name, f) for f in meta.get_fields() if f.concrete)
    if fields is None:
        fields = list(field_map.keys())
    if exclude:
        exclude = set(exclude)
        fields = filter(lambda f: f not in exclude, fields)
    result = [(f, get_formatter_for_field(factory, meta, field_map, f, options)) for f in fields]
    return result


class MetaFormattedModel(type):

    def __init__(cls, name, bases, attrs):
        super(MetaFormattedModel, cls).__init__(name, bases, attrs)
        meta = getattr(cls, 'Meta', None)
        if not meta:
            return
        model = meta.model

        for name, formatter in get_formatters_for_model(cls, model, fields=getattr(meta, 'fields', None),
                                                        exclude=getattr(meta, 'exclude', None),
                                                        options=meta):

            previous = getattr(cls, name, None)
            if not isinstance(previous, Formatter):
                formatter._update_position()
                setattr(cls, name, formatter)
            else:
                previous._update_position()


@six.add_metaclass(MetaFormattedModel)
class FormattedModel(FormattedObject):
    pass


@six.add_metaclass(MetaFormattedModel)
class FormattedModelTable(FormattedTable):
    pass


def object_formatter_factory(model_class, fields=None, exclude=None, **kwargs):
    name = "Formatted%sObject" % model_class.__name__
    meta = type("Meta", (), {"fields": fields, "exclude": exclude, "model": model_class})
    kwargs['Meta'] = meta
    return type(name, (FormattedModel, ), kwargs)


def table_formatter_factory(model_class, fields=None, exclude=None, **kwargs):
    name = "Formatted%sTable" % model_class.__name__
    meta = type("Meta", (), {"fields": fields, "exclude": exclude, "model": model_class})
    kwargs['Meta'] = meta
    return type(name, (FormattedModelTable, ), kwargs)