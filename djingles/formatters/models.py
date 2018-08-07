
from collections import OrderedDict
from django.core.exceptions import FieldDoesNotExist
from django.utils import six
from django.db import models
from .formatters import *
from .base import FormattedObject, FormattedTable, MetaFormattedObject
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
        try:
            field = model._meta.get_field(item)
        except FieldDoesNotExist:
            if hasattr(field, item):
                return Formatter()
            else:
                raise

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

    extant = OrderedDict(factory.base_formatters)
    field_map = OrderedDict((f.name, f) for f in meta.get_fields() if f.concrete)

    if fields is None:
        fields = list(field_map.keys()) + [k for k in extant.keys() if k not in field_map]

    if exclude:
        exclude = set(exclude)
        fields = filter(lambda f: f not in exclude, fields)

    result = []
    for f in fields:
        if f in extant:
            fmt = extant[f]
        else:
            fmt = get_formatter_for_field(factory, meta, field_map, f, options)
        result.append((f, fmt))

    return result


class MetaFormattedModel(MetaFormattedObject):

    def __init__(cls, name, bases, attrs):
        super(MetaFormattedModel, cls).__init__(name, bases, attrs)
        try:
            if cls is FormattedModel or cls is FormattedModelTable:
                return
        except NameError:
            return
        meta = getattr(cls, 'Meta')
        model = meta.model
        base_formatters = []
        for name, formatter in get_formatters_for_model(cls, model, fields=getattr(meta, 'fields', None),
                                                        exclude=getattr(meta, 'exclude', None),
                                                        options=meta):
            # setattr(cls, name, formatter)
            base_formatters.append((name, formatter))
        cls.base_formatters = tuple(base_formatters)

    def subset_class(cls, include=None, exclude=None):
        name = "_Sub%s" % cls.__name__
        fields = cls.base_formatters
        field_names = list(include) if include is not None else [k for k, _ in fields]
        if exclude:
            field_names = [f for f in field_names if f not in set(exclude)]
        meta_class = type("Meta", (cls.Meta, ), {"fields": field_names})
        class_ = type(name, (cls, ), {"Meta": meta_class})
        return class_


class _SubsetMixin:
    pass

@six.add_metaclass(MetaFormattedModel)
class FormattedModel(_SubsetMixin, FormattedObject):
    pass


@six.add_metaclass(MetaFormattedModel)
class FormattedModelTable(_SubsetMixin, FormattedTable):
    pass


def object_formatter_factory(model_class, fields=None, exclude=None, base_class=None, **kwargs):
    name = "Formatted%sObject" % model_class.__name__
    meta = type("Meta", (), {"fields": fields, "exclude": exclude, "model": model_class})
    kwargs['Meta'] = meta
    base_class = base_class or FormattedModel
    return type(name, (base_class, ), kwargs)


def table_formatter_factory(model_class, fields=None, exclude=None, base_class=None, **kwargs):
    name = "Formatted%sTable" % model_class.__name__
    meta = type("Meta", (), {"fields": fields, "exclude": exclude, "model": model_class})
    kwargs['Meta'] = meta
    base_class = base_class or FormattedModelTable
    return type(name, (base_class, ), kwargs)