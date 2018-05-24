
import functools
import jinja2
from django.template.loader import render_to_string
from jinja2.ext import Extension

from djingles import utils


class _Library:

    def __init__(self):
        self.functions = {}
        self.filters = {}
        self.extensions = []


library = _Library()


def jinja2_filter(name=None):
    def closure(func):
        nonlocal name
        if name is None:
            name = func.__name__
        library.filters[name] = func
        return func
    return closure


def jinja2_function(template=None, name=None, takes_context=False, mark_safe=False):
    def closure(orig_func):
        func = orig_func
        wrapper = None
        name_ = name or getattr(func,'_decorated_function', func).__name__

        if template:
            def wrapper(*args, **kwargs):
                from django.template.loader import get_template
                t = get_template(template)
                ctx = orig_func(*args, **kwargs)
                result = t.render(ctx)
                result = jinja2.Markup(result)
                return result
        elif mark_safe:
            def wrapper(*args, **kwargs):
                result = orig_func(*args, **kwargs)
                return jinja2.Markup(result)

        if wrapper:
            func = functools.update_wrapper(wrapper, func)

        if takes_context:
            func = jinja2.contextfunction(func)

        library.functions[name_] = func
        return orig_func

    return closure


class MetaJinja2Function(type):

    def __init__(self, name, bases, attrs):
        super(MetaJinja2Function, self).__init__(name, bases, attrs)
        self.jinja2_name = utils.camel_to_underscore(name)
        library.functions[self.jinja2_name] = self.as_function()


class Jinja2Function(metaclass=MetaJinja2Function):

    template_name = None

    def get_template_names(self):
        return [self.template_name]

    def get_context_data(self):
        return {}

    def render(self):
        ctx = self.get_context_data()
        ctx['me'] = self
        template_names = self.get_template_names()
        content = render_to_string(template_names, ctx)
        return jinja2.Markup(content)

    @classmethod
    def as_function(cls):
        def func(*args, **kwargs):
            instance = cls(*args, **kwargs)
            return instance.render()
        return func


class MetaJinja2Extension(type(Extension)):

    def __init__(self, name, bases, attrs):
        super().__init__(name, bases, attrs)
        library.extensions.append(self)


class Jinja2Extension(Extension, metaclass=MetaJinja2Extension):
    pass