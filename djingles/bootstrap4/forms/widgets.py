
from jinja2 import Markup
from django import forms
from djingles import html
from djingles.forms.widgets import AbstractThemedWidget, ChoiceWidgetMixin


class BootstrapWidget(AbstractThemedWidget):

    error_class = "field-errors"
    label_class = "field-label"
    field_class = "form-group"
    help_class = "help-block"
    failure_class = "has-error"
    success_class = "has-success"
    widget_class = ""
    input_class = "form-control"

    def context_for_field(self, field):
        return {
            "field": field,
            "widget_tag": self.render_widget(field),
            "label": field.label,
            "id_for_label": field.id_for_label,
            "label_tag": self.render_label(field),
            "help": field.help_text,
            "help_tag": self.render_help(field),
            "errors": field.errors,
            "error_tag": self.render_errors(field)
        }

    def render_label(self, field):
        if not field.label:
            return ""
        return html.label(class_=self.label_class, for_=field.id_for_label)[
            field.label
        ]

    def render_help(self, field):
        help_text = field.help_text
        if not help_text:
            return ""
        return html.div(class_=self.help_class)[
            field.help_text
            ]

    def render_errors(self, field):
        errors = field.errors
        return html.ul(class_=self.error_class)[
            [html.li[err] for err in errors]
        ]

    def get_form_property(self, field, property_name, default=None):
        form = field.form
        prop = getattr(form, property_name, None)
        if prop is not None:
            if callable(prop):
                return prop(field.name)
            else:
                return prop.get(field.name)

    def wrap_widget(self, field, content, prefix=None, suffix=None):
        if prefix is None:
            prefix = self.get_form_property(field, "form_input_prefix")
        if suffix is None:
            suffix = self.get_form_property(field, "form_input_suffix")
        if prefix or suffix:
            content = html.div(class_="input-group")[
                html.div(class_="input-group-prepend", if_=prefix is not None)[
                    html.span(class_="input-group-text")[prefix]
                ],
                content,
                html.div(class_="input-group-append", if_=suffix is not None)[
                    html.span(class_="input-group-text")[suffix]
                ]
            ]
        return content

    def render_widget(self, field, prefix=None, suffix=None, hidden=None, form=None):
        widget = field.field.widget
        is_hidden = widget.is_hidden if hidden is None else hidden
        if isinstance(widget, (forms.TextInput, forms.Textarea, forms.Select)):
            widget.attrs["class"] = html.add_css_class(widget.attrs.get("class"), self.input_class, self.widget_class)
            if form:
                widget.attrs['form'] = form
            content = str(field)
        else:
            css_class = ["form-widget", html.widget_css_class(field), self.widget_class]
            if is_hidden:
                css_class.append("form-widget-hidden")
            widget.attrs["class"] = html.add_css_class(widget.attrs.get("class"), self.input_class)
            if form:
                widget.attrs['form'] = form
            content = html.div(class_=css_class)[str(field)]
        content = self.wrap_widget(field, content, prefix, suffix)
        result = str(content)
        return Markup(result)

    def render_field(self, field, layout, **kwargs):
        widget = field.field.widget
        prefix = kwargs.pop("prefix", None)
        suffix = kwargs.pop("suffix", None)
        if widget.is_hidden:
            return self.render_widget(field, prefix=prefix, suffix=suffix, hidden=True)
        for k,v in kwargs.items():
            setattr(field, k, v)
        layout_class = "layout-%s" % layout
        css_classes = ["form-field", html.field_css_class(field), self.field_class, layout_class]
        if field.field.required:
            css_classes.append("required")
        if field.errors:
            css_classes.append(self.failure_class)
        help_text = title = None
        if layout == "inline" and field.help_text:
            title = field.help_text
        else:
            help_text = self.render_help(field)
        return html.div(class_=css_classes, title=title)[
                self.render_label(field),
                self.render_widget(field, prefix=prefix, suffix=suffix),
                help_text,
                self.render_errors(field)
            ]


class BooleanInputMixin:

    def render_subwidget_wrapper(self, content):
        el = super(BooleanInputMixin, self).render_subwidget_wrapper(content)
        el = el(class_="form-check")
        return el

    def render_subwidget(self, code, label, selected, attrs):
        attrs["class"] = html.add_css_class(attrs.get("class", ""), "form-check-input")
        return super(BooleanInputMixin, self).render_subwidget(code, label, selected, attrs)


class RadioSelect(BooleanInputMixin, BootstrapWidget, ChoiceWidgetMixin, forms.RadioSelect):
    input_type = "radio"
    input_class = ""


class CheckboxSelectMultiple(BooleanInputMixin, BootstrapWidget, ChoiceWidgetMixin, forms.CheckboxSelectMultiple):
    input_type = "checkbox"
    input_class = ""


class CheckboxInput(BootstrapWidget, forms.CheckboxInput):

    field_class = "form-group form-check"
    input_class = ""

    def render_widget(self, field, **kwargs):
        if getattr(field, 'layout', None) == 'inline':
            return "%s %s" % (self.render_label(field), str(field))
        else:
            field.field.widget.attrs['class'] = html.add_css_class(field.field.widget.attrs.get("class", ""), "form-check-input")
            return html.div(class_="checkbox")[
                str(field),
                html.label(class_=self.label_class, for_=field.id_for_label)[
                    field.label
                ]
            ]


# class Select(BootstrapWidget, forms.Select):
#     input_class = "form-control bootstrap-select-control"


class SelectMultiple(BootstrapWidget, forms.SelectMultiple):
    input_class = "form-control bootstrap-select-control"


# class ClearableFileInput(BootstrapWidget, forms.ClearableFileInput):
#     widget_class = "custom-file"
#     input_class = "custom-file-input"
#     label_class = "custom-file-label"
#
#     def render_widget(self, field):
#         widget = field.field.widget
#         css_class = ["form-widget", html.widget_css_class(field), self.widget_class]
#         widget.attrs["class"] = html.add_css_class(widget.attrs.get("class"), self.input_class)
#         content = html.div(class_=css_class)[str(field), self.render_label(field)]
#         result = str(content)
#         return result


class SwitchInput(CheckboxInput):
    extra_attrs = {"class": "switch-input"}

    def render_widget(self, field):
        return "%s%s" % (self.render_label(field), str(field))


class DateRangeWidget(forms.MultiWidget):
    pass


class DateInput(BootstrapWidget, forms.DateInput):
    input_type = "date"


class TimeInput(BootstrapWidget, forms.TimeInput):
    input_type = "time"


class DateTimeInput(BootstrapWidget, forms.DateTimeInput):
    input_type = "datetime-local"
    extra_attrs = {"class": "datetimepicker"}


class NumberRangeWidget(forms.NumberInput):
    pass
