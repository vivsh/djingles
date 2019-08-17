import functools
import inspect
from collections import OrderedDict
import random

from django.core.exceptions import ImproperlyConfigured, FieldDoesNotExist
from django.db.models.fields import CharField, TextField
from django.http.request import QueryDict
from django.utils import six
from django import forms
from django.utils.encoding import force_text
from djingles.formatters import Formatter
from djingles.forms.fields import SortField
from djingles import utils


__all__ = ['ActionFormMixin', 'ActionModelForm', 'ActionForm', 'FilterForm',
           'FilterModelForm', 'FilterFormMixin', 'action_model_form_factory']


def _find_decorated_methods(form, attribute):
    for name, func in inspect.getmembers(form, inspect.ismethod):
        if name.startswith("_"):
            continue
        if hasattr(func, attribute):
            yield func


class ActionFormMixin(object):

    confirmation_message = None
    failure_message = None
    success_message = None

    def __init__(self, **kwargs):
        self.context = kwargs.pop("context", {})
        self.action = self.context.get("action", "execute")
        self.context["action"] = self.action
        self.action_method = getattr(self, self.action, self.execute)
        super(ActionFormMixin, self).__init__(**kwargs)
        prepare = getattr(self, 'prepare_%s' % self.action, None)
        if prepare is not None:
            prepare()

    def prepare_if_exists(self, func):
        spec = inspect.getfullargspec(func)
        names = [n for n in spec.args if n != "self"]
        try:
            args = [self.fields[f] for f in names]
        except KeyError:
            pass
        else:
            return func(*args)

    def clean_if_exists(self, func):
        spec = inspect.getfullargspec(func)
        names = [n for n in spec.args if n != "self"]
        try:
            args = [self.cleaned_data[f] for f in names]
            if any(a is None for a in args):
                return
        except KeyError:
            pass
        else:
            return func(*args)

    def __bind_fields(self):
        key = "__bound_with_form"
        for name, field in self.fields.items():
            if hasattr(field, 'bind_form') and not getattr(field, key, False):
                setattr(field, key, True)
                field.bind_form(self)

    def process_context(self, func):
        context = self.context.copy()
        if hasattr(self, "cleaned_data") and hasattr(self, "save"):
            instance = self.save(commit=False)
            context["instance"] = instance
        context["data"] = self.cleaned_data
        spec = inspect.getfullargspec(func)
        if spec.varargs:
            raise ImproperlyConfigured("Form action cannot have variable arguments")
        if spec.varkw:
            return context
        return {k: context[k] for k in spec.args[1:] if k in context}

    def process_result(self, result):
        return result

    @property
    def result(self):
        self.is_valid()
        return self.__result

    def get_success_message(self):
        if self.success_message:
            return self.success_message.format(**self.context)
        return self.success_message

    def get_failure_message(self):
        if self.failure_message:
            return self.failure_message.format(**self.context)
        return self.failure_message

    def get_confirmation_message(self):
        if self.confirmation_message:
            return self.confirmation_message.format(**self.context)
        return self.confirmation_message

    @classmethod
    def class_oid(cls):
        """
        Obfuscated class id
        :return: str
        """
        return utils.create_hash(utils.qualified_name(cls))

    @classmethod
    def call(cls, *kwargs):
        form_obj = cls(**kwargs)
        if not form_obj.is_valid():
            return False, form_obj.errors
        else:
            return True, form_obj.result

    def full_clean(self):
        result = None
        self.__bind_fields()
        super(ActionFormMixin, self).full_clean()
        try:
            _ = self.__result
        except AttributeError:
            try:
                if self.is_bound and not self._errors:
                    method = self.action_method
                    context = self.process_context(method)
                    result = method(**context)
                    result = self.process_result(result)
            except forms.ValidationError as ex:
                self.add_error(None, ex)
            finally:
                self.__result = result

    def select_fields(self, exclude=None, include=None, **extras):
        if exclude is not None:
            for f in exclude:
                self.fields.pop(f, None)
        if include is not None:
            include = set(include)
            for f in list(self.fields.keys()):
                if f not in include:
                    self.fields.pop(f)
        if extras:
            for f in extras:
                self.fields[f] = extras[f]

    def execute(self):
        return {}


class ActionForm(ActionFormMixin, forms.Form):
    pass


class ActionModelForm(ActionFormMixin, forms.ModelForm):

    confirmation_message = "Please confirm that you really wish to {action} this object ?"

    def prepare_delete(self):
        self.select_fields(include=())

    def delete(self):
        self.instance.delete()

    def update(self):
        return self.save()

    def create(self):
        return self.save()

    def clone(self):
        self.instance.id = None
        return self.save()


class FilterFormMixin:

    submit_key = None

    def __init__(self, data=None, *args, **kwargs):
        self.context = kwargs.pop("context", {})
        self.boolean_empty_label = kwargs.pop("boolean_empty_label", "Any")
        self.empty_label = kwargs.pop("empty_label", "--------------")
        unbound = False
        if not data or (self.submit_key and self.submit_key not in data):
            data = None
        super(FilterFormMixin, self).__init__(data=data, *args, **kwargs)
        if self.submit_key:
            self.fields[self.submit_key] = forms.IntegerField(
                widget=forms.HiddenInput,
                required=False
            )
        for key, f in self.fields.items():
            if f.disabled:
                continue
            if isinstance(f, forms.BooleanField):
                field = forms.NullBooleanField(required=False,
                                          label=f.label, help_text=f.help_text)
                self.fields[key] = field
                choices=((1, self.boolean_empty_label),(2, "Yes"), (3, "No"))
                field.widget.choices = choices
            if f.required:
                f.required = False
                if hasattr(f, "choices"):
                    choices = list(f.choices)
                    if choices and choices[0][0]:
                        choices.insert(0, ("", self.empty_label))
                    f.choices = tuple(choices)

    def __bind_fields(self):
        key = "__bound_with_form"
        for name, field in self.fields.items():
            if hasattr(field, 'bind_form') and not getattr(field, key, False):
                setattr(field, key, True)
                field.bind_form(self)

    @property
    def sort_field(self):
        for name, f in self.fields.items():
            if isinstance(f, SortField):
                return self[name]

    def generic_filter(self, name, queryset, value, data):
        kwargs = {}
        if isinstance(value, (tuple, list)):
            name = '%s__in' % name
        kwargs[name] = value
        return queryset.filter(**kwargs)

    def perform_filter(self, queryset):
        self.__bind_fields()
        if not self.is_bound:
            data = {k: self.get_initial_for_field(f, k) for k, f in self.fields.items()}
        else:
            if not self.is_valid():
                return self.invalid_queryset(queryset)
            data = self.cleaned_data
        allowed = set(self.fields.keys())
        if hasattr(self, "before_filters"):
            queryset = self.before_filters(queryset, data)
        for name, value in data.items():
            if name not in allowed or value in (None, '', [], ()):
                continue
            field = self.fields[name]
            if hasattr(self, "filter_%s" % name):
                result = getattr(self, "filter_%s" % name)(queryset, value, data)
            elif hasattr(field, "filter_queryset"):
                result = field.filter_queryset(queryset, value, self[name])
            else:
                result = self.generic_filter(name, queryset, value, data)
            if result is not None:
                queryset = result
        if hasattr(self, "after_filters"):
            queryset = self.after_filters(queryset, data)
        return queryset

    def invalid_queryset(self, queryset):
        return queryset.none()


class FilterForm(FilterFormMixin, forms.Form):
    pass


class FilterModelForm(FilterFormMixin, forms.ModelForm):

    def generic_filter(self, name, queryset, value, data):
        meta = queryset.model._meta
        try:
            field = meta.get_field(name)
        except FieldDoesNotExist:
            return super(FilterModelForm, self).generic_filter(name, queryset, value, data)
        else:
            op = ""
            if isinstance(value, (list, dict)):
                op = "in"
            elif isinstance(field, (CharField, TextField)):
                op = "icontains"
        query = "%s__%s" % (name, op) if op else name
        kwargs = {query: value}
        return queryset.filter(**kwargs)


def action_model_form_factory(model_class, include=None, exclude=(), **kwargs):
    name = "%sActionForm" % model_class.__name__
    meta = type("Meta", (), {"include": include, "exclude": exclude, "model": model_class})
    kwargs['Meta'] = meta
    return type(name, (ActionModelForm, ), kwargs)