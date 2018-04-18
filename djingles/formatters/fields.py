from collections import OrderedDict

import re
from django import forms
from django.utils import six
from django.utils.encoding import force_text
from .base import Formatter

__all__ = ['SortFilterField']


class SortFilterField(forms.ChoiceField):

    def __init__(self, choices=(), toggle=True, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.HiddenInput)
        super(SortFilterField, self).__init__(choices=choices, **kwargs)
        self.toggle = toggle
        self.set_choices(choices)

    def set_choices(self, choices):
        field_map = {}
        new_choices = []
        for i, (value, label) in enumerate(choices):
            position = str(i)
            new_choices.append((position, label))
            field_map[position] = re.sub(r'\s+', ' ', value.strip())
        self.choices = tuple(new_choices)
        self.field_map = field_map

    def valid_value(self, value):
        "Check to see if the provided value is a valid choice"
        text_value = force_text(value)
        if text_value.startswith("-"):
            text_value = text_value[1:]
        return text_value in self.field_map or super(SortFilterField, self).valid_value(text_value)

    def invert_sign(self, name, neg):
        if name.startswith("-"):
            neg = not neg
        return "%s%s" % ("-" if neg else "", name.lstrip("-"))

    def bind_form(self, form):
        formatter_class = form.context.get('formatter_class')
        if formatter_class is None:
            return
        column_dict = OrderedDict(Formatter.extract_from(formatter_class))
        choices = [(name, col.label or name.title()) for name, col in column_dict.items()
                        if col.sortable and not col.hidden]
        self.column_dict = column_dict
        self.set_choices(choices)

    def filter_queryset(self, queryset, key, bound_field):
        neg = key.startswith("-")
        value = self.field_map[key.lstrip("-")]
        invert = lambda a: self.invert_sign(a, neg)
        values = map(invert, value.split())
        return queryset.order_by(*values)

    def filter_queryset(self, queryset, value, bound_field):
        text_value = force_text(value) if value is not None else None
        if not text_value:
            return queryset
        reverse = text_value.startswith("-")
        column_dict = self.column_dict
        name = text_value[1:] if reverse else text_value
        name = self.field_map[name]
        col = column_dict[name]
        if not col.sortable:
            return queryset
        attr = col.attr or name
        if col.reverse:
            reverse = not reverse
        if reverse:
            attr = "-%s" % attr
        return queryset.order_by(attr)


    def get_value_for_name(self, name):
        for value, key in six.iteritems(self.field_map):
            if name == key:
                return value