

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment

from .library import jinja2_filter, jinja2_function, library, Jinja2Function


__all__ = ['jinja2_filter', 'jinja2_function', 'environment', 'Jinja2Function']


def inject_filters(env):
    from django.template.defaultfilters import register
    for name, func in register.filters.items():
        if name not in env.filters:
            env.filters[name] = func


def inject_functions(env):
    pass


def inject_library(env):
    for key, func in library.functions.items():
        env.globals[key] = func

    for key, func in library.filters.items():
        env.filters[key] = func


def jinja2_reverse(view_name, **kwargs):
    extra = kwargs.pop("kwargs", {})
    kwargs.update(extra)
    return reverse(view_name, kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': jinja2_reverse,
    })
    inject_filters(env)
    inject_functions(env)
    inject_library(env)
    return env

