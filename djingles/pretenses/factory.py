
from django.core.exceptions import ValidationError
import contextlib
import pytz.exceptions as pyex
import random
import importlib
from django.conf import settings
from django.db import models
from django.apps import apps
from django.db.utils import IntegrityError
from django.forms.models import model_to_dict
from django.utils.text import camel_case_to_spaces
from . import utils, streams


__all__ = ['register', 'generate']


_processors = {}
_callback = None


def register(pretense, *models):
    if isinstance(pretense, type):
        pretense = pretense()
    for m in models:
        _processors[m] = pretense


def generate(model, n=20, name=None, callback=None):
    global _callback
    _callback = callback
    fac = Factory(model)
    return fac.create_all(n)


def on_create(ins):
    if _callback:
        _callback(model_to_dict(ins))


def boolean():
    return random.choice([True, False])


class IncompleteFactoryError(TypeError):
    pass


@contextlib.contextmanager
def impartial(obj):
    if obj.partial:
        raise IncompleteFactoryError
    obj.partial = True
    yield
    obj.partial = False


def get_file(conf_name, formats=None):
    folder = getattr(settings, conf_name)
    return utils.collect_files(folder, formats)


def get_image_file():
    conf_key = "PRETENSE_IMAGE_DIRS"
    return utils.get_random_image(getattr(settings, conf_key))



class Field(object):

    def __init__(self, field, instance, index):
        self.field = field
        self.instance = instance
        self.index = index

    @property
    def null(self):
        return self.field.null

    @property
    def unique(self):
        return self.field.unique

    @property
    def choices(self):
        choices = getattr(self.field, 'choices', None)
        return list(choices) if choices else choices

    @property
    def primary_key(self):
        return self.field.primary_key

    @property
    def model(self):
        return self.field.related_model

    @property
    def choice(self):
        return random.choice(self.choices)[0]

    def has_choices(self):
        return bool(self.choices)

    def __getattr__(self, item):
        return getattr(self.field, item)

    def set(self, value):
        if self.null and random.choice([True, False]):
            value = None
        setattr(self.instance, self.name, value)

    def __getattr__(self, item):
        return getattr(self.field, item)

    def __repr__(self):
        return "Field(%r)" % self.field


class Factory(object):

    __cache = {}
    __modules = None

    highest_id = 0
    total = 0
    name = None

    def __new__(cls, model):
        if model not in cls.__cache:
            obj = super(Factory, cls).__new__(cls)
            cls.__cache[model] = obj
            obj.model = model
            obj.meta = model._meta
            obj.fields = obj.meta.fields
            Factory.load_pretenses()
        else:
            obj = cls.__cache[model]
        return obj

    def __init__(self, model):
        self.update_stats()

    def update_stats(self):
        self.total = self.model.objects.count()
        self.highest_id = self.model.objects.order_by("id").last().id + 1 if self.total else 0

    @classmethod
    def load_pretenses(cls):
        if cls.__modules is None:
            cls.__modules = []
            for app in apps.get_app_configs():
                name = app.module.__name__
                module_name = "%s.pretenses" % name
                try:
                    mod = importlib.import_module(module_name)
                    cls.__modules.append(mod)
                except ImportError as ex:
                    pass

    @property
    def processors(self):
        classes = [self.model] + list(self.model.__mro__)
        result = []
        for k in classes:
            if k not in _processors:
                continue
            proc = _processors[k]
            result.append(proc)
        result.append(DefaultProcessor(self))
        return result

    def post_save(self, ins):
        method_name = "after_%s_%s" % (self.meta.app_label, self.snake_case(self.model))
        for handler in self.processors:
            func = getattr(handler, method_name, None)
            if callable(func):
                func(ins, FactoryProxy)

    def find_method(self, field, default):
        for handler in self.processors:
            stream = getattr(handler, field.name, None)
            if stream:
                if callable(stream):
                    return stream
                func = getattr(stream, 'next', None)
                if callable(func):
                    return func
            for name in self.method_names(field):
                func = getattr(handler, name, None)
                if callable(func):
                    return func
        return default

    @staticmethod
    def snake_case(cls):
        return camel_case_to_spaces(cls.__name__).lower().replace(" ", "_")

    def method_names(self, field):
        template = "process_%s"
        yield template % self.snake_case(field.__class__)
        for cls in field.__class__.__mro__:
            if issubclass(cls, models.Field):
                yield template % self.snake_case(cls)

    def create(self, index, limit, **kwargs):
        ins = self.model()
        for f in self.fields:
            field = Field(f, ins, index)
            field.total = limit
            name = field.name
            if name in kwargs:
                value = kwargs[name]
            else:
                if field.primary_key:
                    continue
                if field.has_choices():
                    value = field.choice
                else:
                    func = self.find_method(f, self.get_field_value)
                    value = func(field)
            if value is not None:
                field.set(value)
        ins.save()
        for f in self.meta.many_to_many:
            field = Field(f, ins, index)
            func = self.find_method(f, self.get_field_value)
            value = func(field)
            if value is not None:
                field.set(value)
        self.total += 1
        self.highest_id = ins.id
        self.post_save(ins)
        on_create(ins)
        return ins

    def get(self):
        if not self.total:
            self.create_all(10)
        return self.model.objects.order_by("?").first()

    def ensure_total(self, total):
        if self.total < total:
            self.create_all(total - self.total)

    def create_all(self, limit, **kwargs):
        i = 0
        errors = 0
        bulk = []
        while i < limit:
            try:
                ins = self.create(self.highest_id+i, limit, **kwargs)
                i += 1
            except (IntegrityError,
                        ValidationError,
                        pyex.AmbiguousTimeError,
                        pyex.NonExistentTimeError,
                        pyex.InvalidTimeError
                    ) as ex:
                errors += 1
                if errors > limit * 5:
                    raise
            else:
                errors = 0
                bulk.append(ins)
        self.update_stats()
        return bulk

    def get_field_value(self, field):
        return None



class FactoryProxy(object):

    def __init__(self, model):
        self.factory = Factory(model)

    def create(self, limit, **kwargs):
        return self.factory.create_all(limit, **kwargs)


class DefaultProcessor(object):

    def __init__(self, factory):
        self.factory = factory

    def process_float_field(self, field):
        return streams.FloatStream().next(field)

    def process_decimal_field(self, field):
        return streams.DecimalStream().next(field)

    def process_null_boolean_field(self, field):
        return boolean()

    def process_boolean_field(self, field):
        return boolean()

    def process_positive_small_integer_field(self, field):
        return streams.IntegerStream(end=2**6).next(field)

    def process_positive_integer_field(self, field):
        return streams.IntegerStream(end=2**24).next(field)

    def process_small_integer_field(self, field):
        return streams.IntegerStream(end=2**6).next(field)

    def process_big_integer_field(self, field):
        return streams.IntegerStream(end=2*24).next(field)

    def process_integer_field(self, field):
        return streams.IntegerStream(end=2**10).next(field)

    def process_slug_field(self, field):
        return streams.SlugStream().next(field)

    def process_char_field(self, field):
        return streams.SentenceStream().next(field)[: field.max_length]

    def process_text_field(self, field):
        return streams.ParagraphStream().next(field)

    def process_foreign_key(self, field):
        if field.null:
            return None
        index = field.index
        factory = Factory(field.model)
        value = factory.get()
        return value

    def process_date_time_field(self, field):
        return streams.DateTimeStream().next(field)

    def process_date_field(self, field):
        return streams.DateStream().next(field)

    def process_time_field(self, field):
        return streams.TimeStream().next(field)

    def process_username(self, field):
        word = streams.FirstNameStream().next(field)
        return "%s%s" % (word, field.index)

    def process_ip_address_field(self, field):
        return streams.IPAddressStream().next(field)

    def process_generic_ip_address_field(self, field):
        return self.process_ip_address_field(field)

    def process_json_field(self, field):
        return {}

    def process_password(self, field):
        word = streams.FirstNameStream().next(field)
        field.instance.set_password(word)

    def process_point_field(self, field):
        return streams.PointStream().next(field)

    def process_image_field(self, field):
        return streams.ImageStream(settings.GINGER_PRETENSE_IMAGE_DIRS).next(field)
