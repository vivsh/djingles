from django.core.paginator import Page

from djingles.jinja2.functions import form_start, form_end
from djingles.jinja2 import jinja2_function
from djingles import html
from djingles.bootstrap4.forms import widgets


@jinja2_function()
def bs4_widget(field, **kwargs):
    return widgets.BootstrapWidget.widget_to_html(field, **kwargs)


@jinja2_function()
def bs4_field(field, layout="stack", **kwargs):
    return widgets.BootstrapWidget.field_to_html(field, layout, **kwargs)


@jinja2_function(takes_context=True, mark_safe=True)
def bs4_form_start(context, form, **attrs):
    attrs['class'] = "%s" % attrs.pop("class", "")
    return form_start(context, form, **attrs)


@jinja2_function(mark_safe=True)
def bs4_form_end(form):
    return form_end(form)


@jinja2_function(mark_safe=True)
def bs4_form_submit(form, label="Submit", icon="fa fa-save", **kwargs):
    return html.button(type="submit", class_="btn btn-primary", **kwargs)[
        html.i(class_=icon) if icon else None, " ",
        label
    ]


@jinja2_function(mark_safe=True)
def bs4_form_reset(form, label="Submit", icon="fa fa-erase", **kwargs):
    return html.button(type="reset", class_="btn btn-primary", **kwargs)[
        html.i(class_=icon) if icon else None, " ",
        label
    ]


@jinja2_function(mark_safe=True)
def bs4_form_actions(form, submit="Submit", reset=None):
    return html.div(class_="form-actions")[
        bs4_form_reset(form, label=reset) if reset else None,
        bs4_form_submit(form, label=submit) if submit else None,
    ]


@jinja2_function(mark_safe=True, template="bootstrap4/partials/pagination.html")
def bs4_pagination(page, request):
    num_pages = 0 if not isinstance(page, Page) else page.paginator.num_pages
    return {
        "num_pages": num_pages,
        "object": page,
        "request": request
    }