
from importlib import import_module
import pkgutil
from django.utils.module_loading import module_has_submodule
import os
import threading
import re
import hashlib
from collections import deque
import inspect
import base64
import pickle
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.db import models
from django.apps import apps
from urllib import parse


first_cap_re = re.compile('(.)([A-Z][a-z]+)')

all_cap_re = re.compile('([a-z0-9])([A-Z])')



def camel_to_underscore(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def camel_to_hyphen(name):
    s1 = first_cap_re.sub(r'\1-\2', name)
    return all_cap_re.sub(r'\1-\2', s1).lower()


def join_with_underscore(*args):
    return '_'.join( str(a) for a in args if a )

def hyphen_to_camel(value):
    return "".join([x.title() for x in value.split('-')])

def underscore_to_camel(value):
    return "".join([x.title() for x in value.split('_')])


def page_number_range(index, limit, total):
    """
    :param index: Current page number
    :param limit: Maximum number of pages
    :param total: Total number of pages
    :return: iterator of int
    """
    index = max(min(total, index), 1)
    head = int((limit-1)/2)
    tail = limit - head
    first = max(index-head, 1)
    last = min(first+limit-1, total)
    if index+tail > last:
        first -= index+tail-last-1
    return range(max(first, 1), last+1)


def url_query_update(url, values, append=False):
    parts = parse.urlsplit(url)
    params = parse.parse_qs(parts.query)
    for key, value in values.items():
        if key not in params or not append:
            params[key] = value if isinstance(value, (list, tuple)) else [value]
        else:
            if isinstance(value, (list, tuple)):
                params[key].extend(value)
            else:
                params[key].append(value)
    return parts._replace(query=parse.urlencode(params, True)).geturl()


def qualified_name(cls):
    """
    Return fully-qualified name for classes and functions. Doesn't differentiate between
    bound and unbound methods
    :param cls:
    :return: str fully qualified name
    """
    # if hasattr(cls, "__qualname__"):
    #     return getattr(cls,"__qualname__")
    if inspect.ismodule(cls):
        return cls.__name__
    parts = [cls.__name__]
    if inspect.ismethod(cls):
        parts.append(cls.im_class.__name__)
    parts.append(cls.__module__)
    return ".".join(reversed(parts))


def create_hash(*args):
    """
    Returns a string representation of the provided arguments.
    Intended for use in other functions
    :param args: list of python objects
    :return: str
    """
    md = hashlib.md5()
    for a in args:
        md.update(repr(a).encode('utf-8'))
    return md.hexdigest()


def get_form_name(form_class_or_obj):
    form_class = form_class_or_obj if inspect.isclass(form_class_or_obj) else form_class_or_obj.__class__
    name = form_class.__qual_name__
    return create_hash(name)


def auth_login(request,user):
    from django.contrib.auth import login
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request,user)
    return user


def get_age(born):
    today = timezone.now().date()
    if not born: return 0
    try: # raised when birth date is February 29 and the current year is not a leap year
        birthday = born.replace(year=today.year)
    except ValueError:
        birthday = born.replace(year=today.year, day=born.day-1)
    if birthday > today:
        return today.year - born.year - 1
    else:
        return today.year - born.year


def get_request_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_request_latlng(request):
    from django.contrib.gis.geoip import GeoIP
    g = GeoIP()
    ip = get_request_ip(request)
    return g.lat_lon(ip)


def model_from_dict(model, kwargs, many_to_many=False):
    instance = model()
    model_update_from_dict(instance, kwargs, many_to_many=many_to_many)
    return instance


def model_to_dict(instance, fields=None, exclude=None):
    from django.db.models.fields.related import ManyToManyField, ForeignKey
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.virtual_fields + opts.many_to_many:
        if fields and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if isinstance(f, ForeignKey):
            data[f.get_attname()] = f.value_from_object(instance)
        elif isinstance(f, ManyToManyField):
            # If the object doesn't have a primary key yet, just use an empty
            # list for its m2m fields. Calling f.value_from_object will raise
            # an exception.
            if instance.pk is None:
                data[f.name] = []
            else:
                # MultipleChoiceWidget needs a list of pks, not object instances.
                qs = f.value_from_object(instance)
                if qs._result_cache is not None:
                    data[f.name] = [item.pk for item in qs]
                else:
                    data[f.name] = list(qs.values_list('pk', flat=True))
        else:
            data[f.name] = f.value_from_object(instance)
    return data


def model_update_from_dict(instance, kwargs, many_to_many=False):
    meta = instance.__class__._meta
    names = set(f.name for f in meta.get_fields())
    if not many_to_many:
        names.difference_update({a.name for a in meta.many_to_many})
    for k in names:
        if k in kwargs:
            setattr(instance, k, kwargs[k])


def update_object(instance, data):
    opts = instance._meta
    file_field_list = []
    # Wrap up the saving of m2m data as a function.
    def save_m2m():
        for f in opts.many_to_many:
            if f.name in data:
                f.save_form_data(instance, data[f.name])

    for f in opts.fields:
        if f.name not in data or isinstance(f, models.AutoField):
            continue
        if isinstance(f, models.FileField):
            file_field_list.append(f)
        else:
            f.save_form_data(instance, data[f.name])

    for f in file_field_list:
        f.save_form_data(instance, data[f.name])

    return save_m2m


def base64pickle_loads(data):
    encoded_data = base64.b64decode(force_bytes(data))
    return pickle.loads(encoded_data)


def base64pickle_dumps(data):
    serialized = pickle.dumps(data)
    return base64.b64encode(serialized).decode("ascii")


def iter_app_modules(module_name, deep=False):
    for config in apps.get_app_configs():
        package = config.module
        if module_has_submodule(package, module_name):
            full_name = "%s.%s" %(package.__name__, module_name)
            module = import_module(full_name)
            if not deep:
                yield module
            else:
                try:
                    pkg_path = module.__path__
                except AttributeError:
                    yield module
                else:
                    for importer, modname, ispkg in pkgutil.iter_modules(pkg_path):
                        if not ispkg:
                            yield importer.find_module(modname).load_module(modname)


def cm_to_feet_inches(value):
    v = float(value)
    feet = int(round(v / 30.48, 1))
    inches = int(round((v - feet * 30.48) / 2.54, 0))
    return feet, inches


def feet_inches_to_cm(feet, inches):
    result = int(round((feet * 12 + inches) * 2.54, 0))
    return result


def flatten(values):
    stack = deque(values)
    while stack:
        item = stack.popleft()
        if isinstance(item, (list, tuple)):
            stack.extendleft(reversed(item))
        else:
            yield item


def get_related_field(model, field_name):
    parts = field_name.split("__")
    field_name = parts.pop(0)
    field = model._meta.get_field(field_name)
    while parts and field.model:
        model = field.related_model
        item = parts.pop(0)
        field = model._meta.get_field(item)
    return field
