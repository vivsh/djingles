
import inspect
from django.forms.formsets import BaseFormSet
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from djingles.jinja2 import jinja2_function
from djingles import html
from django.utils import timezone


@jinja2_function(takes_context=True, mark_safe=True)
def field_option_tags(field):
    result = []
    for choice in html.field_choices(field):
        tag = html.option(value=choice.value, selected=choice.selected)[choice.content]
        result.append(tag.render())
    return "".join(result)


@jinja2_function(takes_context=True, mark_safe=True)
def form_hidden_field_tags(context, form, csrf=False):
    request = context["request"]
    fields = []
    if csrf:
        fields.append(html.form_csrf_tag(request))
    if not isinstance(form, BaseFormSet):
        for f in form.hidden_fields():
            fields.append(str(f))
    return "".join(fields)


@jinja2_function()
def field_range(form, *args, **kwargs):
    return html.field_range(form, *args, **kwargs)


@jinja2_function()
def field_iter(form, *names):
    return html.iter_fields(form, names)


@jinja2_function(mark_safe=True)
def form_attrs(form, **kwargs):
    return html.form_attrs(form, **kwargs)


@jinja2_function(takes_context=True, mark_safe=True)
def form_start(context, form, **attrs):
    csrf = attrs.get("method", "post").lower() == "post"
    attrs = html.form_attrs(form, **attrs)
    form_tag = "<form {}>".format(attrs)
    hidden = form_hidden_field_tags(context, form, csrf=csrf)
    mgmt = force_text(getattr(form, "management_form", ""))
    return "%s%s%s" % (form_tag, hidden, mgmt)


@jinja2_function(mark_safe=True)
def form_end(form):
    return mark_safe("</form>")


@jinja2_function()
def field_choices(field):
    return html.field_choices(field)


@jinja2_function()
def field_links(request, field):
    return html.field_links(request, field)


@jinja2_function()
def field_help(field):
    return field.help_text

@jinja2_function()
def field_errors(field):
    return field.errors


@jinja2_function()
def field_label(field):
    return field.label


@jinja2_function()
def field_id(field):
    return field.id_for_label


@jinja2_function()
def field_name(field):
    return field.html_name


@jinja2_function()
def field_value(field):
    return field.value()


@jinja2_function(mark_safe=True)
def widget_tag(field, **attrs):
    return html.render_widget(field, *attrs)


@jinja2_function(mark_safe=True)
def field_tag(field, layout=None, **kwargs):
    return html.render_field(field, layout=layout, **kwargs)


@jinja2_function()
def field_class(field):
    return html.field_css_class(field)


@jinja2_function()
def form_class(form):
    return html.make_css_class(form)


@jinja2_function()
def widget_class(field):
    return html.widget_css_class(field)


@jinja2_function()
def field_is(field, class_name):
    return class_is(field.field, class_name)


@jinja2_function()
def widget_is(field, class_name):
    return class_is(field.field.widget, class_name)


@jinja2_function()
def form_visible_fields(form):
    return form.visible_fields()


@jinja2_function()
def class_is(obj, class_name):
    class_ = obj.__class__
    return class_.__name__ == class_name or any(class_name == b.__name__ for b in inspect.getmro(class_))


@jinja2_function()
def build_links(obj, request, *args, **kwargs):
    return html.build_links(obj, request, *args, **kwargs)

@jinja2_function()
def now():
    return timezone.now()


@jinja2_function()
def model_verbose_name(obj):
    return obj._meta.verbose_name.title()


@jinja2_function()
def model_verbose_name_plural(obj):
    return obj._meta.verbose_name_plural.title()