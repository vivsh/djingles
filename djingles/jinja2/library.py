
import functools
import jinja2


class _Library:

    def __init__(self):
        self.functions = {}
        self.filters = {}


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