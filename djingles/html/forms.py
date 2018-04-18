
from django.forms.widgets import CheckboxInput
import re
from collections import namedtuple
from django.middleware import csrf
from django.utils import six
from django.utils.encoding import force_text
from djingles import utils
from . import common


__all__ = ["Choice", "Link", "form_csrf_tag", "form_attrs", "form_css_class",
           "field_choices", "field_name_range", "field_links", "iter_fields", "widget_css_class",
           "render_widget", "register_layout", "render_field", "field_css_class", "field_range",
           "render_page", "wrap_csrf_token", "is_selected_choice", "make_css_class"]


Choice = namedtuple("Choice", ["name", "value", "content", "selected"])


class Link(object):

    def __init__(self, url, content, is_active=False, **kwargs):
        self.url = url
        self.content = content
        self.is_active = is_active
        for k in kwargs:
            setattr(self, k, kwargs[k])


_layouts = {}


def make_css_class(obj, suffix=""):
    name = utils.camel_to_hyphen(re.sub(r'(?i)widget|field|ginger|form|input', '', obj.__class__.__name__, 1))
    if suffix:
        name = "%s%s" % (name, suffix)
    return name


def is_selected_choice(values, choice):
    if not isinstance(values, (list, tuple)):
        values = (values, )
    text_choice = force_text(choice)
    for v in values:
        if v == choice or text_choice == force_text(v):
            return True
    return False


def field_choices(field):
    form_field = field.field
    field_value = field.value()
    name = field.html_name
    for code, label in form_field.choices:
        is_active = is_selected_choice(field_value, code)
        yield Choice(name, code, label, is_active)


def field_links(request, field):
    url = request.get_full_path()
    form_field = field.field
    field_value = field.value()
    if hasattr(form_field, 'build_links'):
        for value in form_field.build_links(request, field):
            yield value
    else:
        for code, label in form_field.choices:
            is_active = is_selected_choice(field_value, code)
            link_url = utils.url_query_update(url, {field.name: code})
            yield Link(link_url, label, is_active, value=code)


def form_attrs(form, **kwargs):
    attrs = kwargs
    attrs.setdefault("method", "post")
    classes = attrs.pop("class", "")
    if isinstance(classes, six.string_types):
        classes = classes.split(" ")
    classes.append(form_css_class(form))
    attrs["class"] = classes
    attrs['enctype']='multipart/form-data' if form.is_multipart() else 'application/x-www-form-urlencoded'
    return common.html_attrs(attrs)


def form_csrf_tag(request):
    csrf_token = csrf.get_token(request)
    el = common.input(type_="hidden", name="csrfmiddlewaretoken", value=csrf_token)
    return el.render()


def wrap_csrf_token(token):
    el = common.input(type_="hidden", name="csrfmiddlewaretoken", value=token)
    return el.render()


def field_range(form, start, end, step=None, hidden=True):
    field_names = field_name_range(form, start, end, step)
    return iter_fields(form, field_names, hidden=hidden)


def field_name_range(form, first, last, step=None, field_names=None):
    if field_names is None:
        field_names = list(form.fields.keys())
    keys = field_names
    if first is not None and isinstance(first, six.string_types):
        try:
            first = keys.index(first)
        except ValueError:
            raise KeyError("%r is not a field for form %r" % (first, form.__class__.__name__))
    if last is not None and isinstance(last, six.string_types):
        try:
            last = keys.index(last)-1
        except ValueError:
            raise KeyError("%r is not a field for form %r" % (last, form.__class__.__name__))
    return keys[first:last:step]


def iter_fields(form, names, hidden=True):
    for name in names:
        field = form[name]
        if hidden or not field.hidden:
            yield field


def render_field(field, layout=None, **kwargs):
    if field.is_hidden:
        return field.as_hidden()
    layout = _layouts.get(layout, default_layout)
    template = layout(field)
    ctx = {
        "field": field,
        "label": field.label,
        "label_tag": common.label(class_="form-label", for_=field.id_for_label)[field.label] if field.label else "",
        "widget": render_widget(field),
        "help": field.help_text,
        "help_tag": common.div(class_="form-help")[field.help_text],
        "errors": field.errors
    }
    content = template.format(**ctx)
    classes = ["form-field", field_css_class(field)]
    if field.errors:
        classes.append("has-error")
    return common.div(class_=classes,
                      data_field=field.name, **kwargs)[content]


def render_widget(field, **attrs):
    el = common.div(**attrs)[str(field)]
    el.attrib.update(class_=[widget_css_class(field), "form-widget"])
    return el.render()


def register_layout(name, func):
    _layouts[name] = func


def default_layout(field):
    if isinstance(field.field.widget, CheckboxInput):
        return "{widget}{label_tag}{help}{errors}"
    return "{label_tag}{widget}{help}{errors}"


def field_css_class(field):
    return make_css_class(field.field, "-field")


def widget_css_class(field):
    return make_css_class(field.field.widget, "-widget")


def form_css_class(form):
    return make_css_class(form, "-form")


def render_page(request, page, previous="&laquo;", next="&raquo;", **kwargs):
    # if isinstance(page, GingerDataSet):
    #     page = page.object_list
    if page.paginator.num_pages <= 1:
        return ""
    H = common
    nav = H.ul(class_="pagination", **kwargs)
    if page.has_previous():
        url = page.previous_link(request).url
        previous_tag = H.li(aria_label="Previous")[H.a(href=url)[previous]]
        nav.append(previous_tag)
    for link in page.build_links(request):
        if link.is_active:
            el = H.li(class_="active")[H.span[link.content]]
        else:
            el = H.li[H.a(href=link.url)[link.content]]
        nav.append(el)
    if page.has_next():
        url = page.next_link(request).url
        next_tag = H.li(aria_label="Next")[H.a(href=url)[next]]
        nav.append(next_tag)
    return nav.render()