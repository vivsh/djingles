
from django import forms
from djingles import html
from djingles.forms.widgets import AbstractThemedWidget, ChoiceWidgetMixin


class BootstrapWidget(AbstractThemedWidget):

    error_class = "field-error"
    label_class = "control-label"
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

    def render_widget(self, field):
        widget = field.field.widget
        if isinstance(widget, (forms.TextInput, forms.Textarea, forms.Select)):
            widget.attrs["class"] = html.add_css_class(widget.attrs.get("class"), self.input_class, self.widget_class)
            content = str(field)
        else:
            css_class = ["form-widget", html.widget_css_class(field), self.widget_class]
            widget.attrs["class"] = html.add_css_class(widget.attrs.get("class"), self.input_class)
            content = html.div(class_=css_class)[str(field)]
        result = "%s%s" % (self.render_label(field), str(content))
        return result

    def render_field(self, field, layout):
        layout_class = "layout-%s" % layout
        css_classes = [html.field_css_class(field), self.field_class, layout_class]
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
                self.render_widget(field),
                help_text,
                self.render_errors(field)
            ]


class BooleanInputMixin:
    def render_subwidget_wrapper(self, content):
        el = super().render_subwidget_wrapper(content)
        el = el(class_="form-check")
        return el

    def render_subwidget(self, code, label, selected, attrs):
        attrs["class"] = html.add_css_class(attrs.get("class", ""), "form-check-input")
        return super().render_subwidget(code, label, selected, attrs)


class RadioSelect(BooleanInputMixin, BootstrapWidget, ChoiceWidgetMixin, forms.RadioSelect):
    input_type = "radio"
    input_class = ""


class CheckboxSelectMultiple(BooleanInputMixin, BootstrapWidget, ChoiceWidgetMixin, forms.CheckboxSelectMultiple):
    input_type = "checkbox"
    input_class = ""


class CheckboxInput(BootstrapWidget, forms.CheckboxInput):

    field_class = "form-group form-check"
    input_class = ""

    def render_widget(self, field):
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
    input_type = "datetime"
    extra_attrs = {"class": "datetimepicker"}


class NumberRangeWidget(forms.NumberInput):
    pass
