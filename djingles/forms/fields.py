
import re
import warnings
import mimetypes
# import urllib2
from django.utils.encoding import force_text
from django.utils import six
import os
from urllib.request import urlopen
from urllib.parse import urlparse
from django import forms
from django.core.validators import URLValidator
from django.core.files.uploadedfile import SimpleUploadedFile

from djingles import utils
from djingles.utils import feet_inches_to_cm, cm_to_feet_inches


__all__ = ["FileOrUrlInput", "HeightField", "HeightWidget", "SortField", "GingerDataSetField", "GingerSortField", 
           "GingerPageField"]


class FileOrUrlInput(forms.ClearableFileInput):
    
    def download_url(self, name, url):
        validate = URLValidator()
        try:
            validate(url)
        except forms.ValidationError as _:
            raise
            return None
        
        parsed_url = urlparse(url)
        path = parsed_url[2].strip("/")
        name = os.path.basename(path)
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        ze_file = opener.open(url).read()
        file_obj = SimpleUploadedFile(name=name, content=ze_file, content_type=mimetypes.guess_type(name))
        file_obj.url = url
        return file_obj

    def value_from_datadict(self, data, files, name):
        if name in data and name not in files:
            url = forms.HiddenInput().value_from_datadict(data, files, name)
            result = self.download_url(name, url) if url and isinstance(url, six.string_types) else None
            files = files.copy() if files else {}
            files[name] = result
        return super(FileOrUrlInput, self).value_from_datadict(data, files, name)


class HeightWidget(forms.MultiWidget):

    def __init__(self, *args, **kwargs):
        widgets = [forms.TextInput(attrs={'placeholder': '5', 'size': '3'}), forms.TextInput(attrs={'placeholder': '6',
                                                                                                    'size': '3'})]
        super(HeightWidget,self).__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if value:
            result = cm_to_feet_inches(value)
            return result
        else:
            return [None,None]

    def format_output(self, rendered_widgets):
        return "%s ft   %s inches" % tuple(rendered_widgets)


class HeightField(forms.MultiValueField):
    widget = HeightWidget

    def __init__(self, *args, **kwargs):
        kwargs.pop('min_value',None)
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        reqd = kwargs.setdefault('required', False)
        fields = (
            forms.IntegerField(min_value=0,required=reqd),
            forms.IntegerField(min_value=0,required=reqd),
        )
        super(HeightField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list and all(d is not None for d in data_list):
            feet, inches = data_list
            return feet_inches_to_cm(feet, inches)
        return None


class GingerSortField(forms.ChoiceField):

    def __init__(self, choices=(), toggle=True, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.HiddenInput)
        super(GingerSortField, self).__init__(choices=choices, **kwargs)
        self.toggle = toggle
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
        return text_value in self.field_map or super(GingerSortField, self).valid_value(text_value)

    def build_links(self, request, bound_field):
        value = bound_field.value()
        field_name = bound_field.name
        text_value = force_text(value) if value is not None else None
        for k, v in self.choices:
            content = force_text(v)
            key = force_text(k)
            is_active = text_value and text_value == key
            if is_active and self.toggle:
                next_value = key if text_value.startswith("-") else "-%s" % key
            else:
                next_value = key
            url = utils.get_url_with_modified_params(request, {field_name: next_value})
            yield ui.Link(url=url, content=content, is_active=is_active)

    def invert_sign(self, name, neg):
        if name.startswith("-"):
            neg = not neg
        return "%s%s" % ("-" if neg else "", name.lstrip("-"))

    def handle_queryset(self, queryset, key, bound_field):
        neg = key.startswith("-")
        value = self.field_map[key.lstrip("-")]
        invert = lambda a: self.invert_sign(a, neg)
        values = map(invert, value.split())
        return queryset.order_by(*values)

    def get_value_for_name(self, name):
        for value, key in six.iteritems(self.field_map):
            if name == key:
                return value


class GingerDataSetField(GingerSortField):

    def __init__(self, dataset_class, process_list=False, **kwargs):
        column_dict = dataset_class.get_column_dict()
        self.reverse = kwargs.pop("reverse", False)
        choices = [(name, col.label or name.title()) for name, col in six.iteritems(column_dict) if not col.hidden]
        super(GingerDataSetField, self).__init__(choices=choices, **kwargs)
        self.dataset_class = dataset_class
        self.process_list = process_list

    def handle_queryset(self, queryset, value, bound_field):
        text_value = force_text(value) if value is not None else None
        if not text_value:
            return queryset
        reverse = text_value.startswith("-")
        column_dict = self.dataset_class.get_column_dict()
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

    def handle_dataset(self, dataset, value, bound_field):
        text_value = force_text(value) if value is not None else None
        if not text_value:
            return
        reverse = text_value.startswith("-")
        value = text_value[1:] if reverse else text_value
        name = self.field_map[value]
        column = dataset.columns[name]
        if column.reverse:
            reverse = not reverse
        column.sort(reverse=reverse)


class SortField(GingerSortField):

    def __init__(self, *args, **kwargs):
        super(SortField, self).__init__(*args, **kwargs)
        warnings.warn("Please use GingerSortField instead of SortField", DeprecationWarning)

