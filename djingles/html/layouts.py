
from django.conf import settings
import importlib
from django.utils.encoding import force_text
from . import common as html, forms

engines = None


__all__ = ['get_engine', 'render_form', 'render_column',
           'render_container', 'render_row', 'render_form_end', 'render_form_field',
           'render_form_footer', 'render_form_header', 'render_form_start', 'row', 'container', 'col', 'field']


def get_engine(name="default"):
    global engines
    if engines is None:
        engines = {}
    if name not in engines:
        config = getattr(settings, "GINGER_FRONTEND_ENGINE", {"default": "ginger.html.layouts.FrontendEngine"})
        module_name, class_name = config[name].rsplit(".", 1)
        module = importlib.import_module(module_name)
        engine = getattr(module, class_name)()
        engines[name] = engine
    return engines[name]


def render_form_field(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.form_field(*args, **kwargs)


def render_form(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.form(*args, **kwargs)


def render_form_start(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.form_start(*args, **kwargs)


def render_form_end(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.form_end(*args, **kwargs)


def render_form_header(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.form_header(*args, **kwargs)


def render_form_footer(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.form_footer(*args, **kwargs)


def render_row(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.row(*args, **kwargs)


def render_column(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.column(*args, **kwargs)


def render_container(name, *args, **kwargs):
    engine = get_engine(name)
    return engine.container(*args, **kwargs)



class FrontendEngine(object):

    def form_hidden_field(self, context, field):
        return force_text(field)

    def form_csrf(self, context):
        request = context['request']
        return forms.form_csrf_tag(request)

    def form_start(self, context, form, **attrs):
        is_csrf = attrs.get("method", "post").lower() == "post"
        attrs = forms.form_attrs(form, **attrs)
        form_tag = "<form {}>".format(attrs)
        mgmt = force_text(getattr(form, "management_form", ""))
        csrf = self.form_csrf(context) if is_csrf else ""
        return "%s%s%s" % (form_tag, csrf, mgmt)

    def form_end(self, context, form , **attrs):
        return "</form>"

    def form_visible_field(self, context, field):
        return force_text(field)

    def form_header(self, context, form):
        return ""

    def form_footer(self, context, form):
        return ""

    def form_field(self, context, tag):
        field = tag.field
        return self.form_visible_field(context, field) if field.is_hidden \
            else self.form_hidden_field(context, field)

    def row(self, context, tag):
        return tag.mutate(html.div(class_="row"))

    def column(self, context, tag):
        return tag.mutate(html.div(class_="col-md-2"))

    def container(self, context, tag):
        return tag.mutate(html.div(class_="container"))

    def form(self, context, form, **attrs):
        start = self.form_start(context, form, **attrs)
        end = self.form_end(context, form, **attrs)
        if hasattr(form, "render"):
            content = html.empty[form.render(context, **attrs)]
            fields = force_text(content.render(context, **attrs))
        else:
            fields = " ".join([self.form_field(context, f) for f in form])
        header = self.form_header(context, form)
        footer = self.form_footer(context, form)
        errors = self.form_non_field_errors(context, form)
        return "{start}{errors}{header}{fields}{footer}{end}".format(**locals())

    def form_non_field_errors(self, context, form):
        return force_text(form.non_field_errors())


class Container(html.Element):
    def render(self, context, *args, **kwargs):
        engine = get_engine()
        return str(engine.container(context, self, *args, **kwargs))


class Column(html.Element):
    def render(self, context, *args, **kwargs):
        engine = get_engine()
        return str(engine.column(context, self, *args, **kwargs))


class Row(html.Element):
    def render(self, context, *args, **kwargs):
        engine = get_engine()
        return str(engine.row(context, self, *args, **kwargs))


class Field(html.Element):

    def __init__(self, *args, **kwargs):
        super(Field, self).__init__("div")

    def __call__(self, field, **kwargs):
        cp = super(Field, self).__call__(**kwargs)
        cp.field = field
        return cp

    def render(self, ctx, *args, **kwargs):
        engine = get_engine()
        return str(engine.form_field(ctx, self, *args, **kwargs))


row = Row("div")
field = Field()
col = Column("div")
container = Container("div")