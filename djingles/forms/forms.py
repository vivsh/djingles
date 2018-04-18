
import inspect
from collections import OrderedDict

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django import forms
from django.utils.encoding import force_text
from djingles.formatters import Formatter
from djingles.forms.fields import GingerSortField
from djingles import utils


__all__ = ['ActionFormMixin', 'ActionModelForm', 'ActionForm', 'TableSortField', 'FilterForm',
           'FilterModelForm', 'FilterFormMixin', 'action_model_factory']


class ActionFormMixin(object):

    confirmation_message = None
    failure_message = None
    success_message = None

    def __init__(self, **kwargs):
        self.optional_fields = kwargs.pop("optional_fields", set())
        parent_cls = forms.Form if not isinstance(self, forms.ModelForm) else forms.ModelForm
        constructor = parent_cls.__init__
        parent_constructor = super(ActionFormMixin, self).__init__
        keywords = set(inspect.getargspec(constructor).args)
        func = lambda a: getattr(a, 'im_func', a)
        parent_keywords = set(inspect.getargspec(parent_constructor).args) \
            if func(parent_constructor) is not func(constructor) else set()
        context = {}
        for key in kwargs.copy():
            if key in keywords and key not in parent_keywords:
                continue
            value = kwargs.pop(key) if key not in parent_keywords else kwargs.get(key)
            context[key] = value
        super(ActionFormMixin, self).__init__(**kwargs)
        self.context = context
        prepare = getattr(self, 'prepare_%s' % self.get_action_name(), None)
        if prepare is not None:
            prepare()

    def get_action_name(self):
        return self.context.get("action", "execute")

    def get_action_method(self):
        func = self.get_action_name() or 'execute'
        return getattr(self, func)

    def __bind_fields(self):
        key = "__bound_with_form"
        optionals = set(self.optional_fields if self.optional_fields is not None else self.fields.keys())
        for name, field in self.fields.items():
            if name in optionals:
                field.required = False
            if hasattr(field, 'bind_form') and not getattr(field, key, False):
                setattr(field, key, True)
                field.bind_form(self)

    def process_context(self, func=None):
        context = self.context.copy()

        if hasattr(self, "cleaned_data") and hasattr(self, "save"):
            instance = self.save(commit=False)
            context["instance"] = instance

        context["data"] = self.cleaned_data

        spec = inspect.getargspec(func or self.get_action_method())
        if spec.varargs:
            raise ImproperlyConfigured("Form action cannot have variable arguments")
        if spec.keywords:
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
        return cls(**kwargs).run()

    def run(self):
        if not self.is_valid():
            return False, self.errors
        else:
            return True, self.result

    def full_clean(self):
        self.__bind_fields()
        super(ActionFormMixin, self).full_clean()
        try:
            _ = self.__result
        except AttributeError:
            result = None
            try:
                if self.is_bound and not self._errors:
                    context = self.process_context()
                    result = self.get_action_method()(**context)
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

    def execute(self, **kwargs):
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


class FilterFormMixin(ActionFormMixin):

    def __init__(self, queryset, **kwargs):
        self.queryset = queryset
        kwargs.setdefault("optional_fields", None)
        super(FilterFormMixin, self).__init__(**kwargs)

    def perform_action(self):
        queryset = self.perform_filter()
        action = self.get_action_method()
        return action(queryset)

    def perform_filter(self):
        queryset = self.queryset
        if not self.is_valid():
            return self.invalid_queryset(queryset)
        data = self.cleaned_data
        allowed = set(self.fields.keys())
        if hasattr(self, "before_filters"):
            queryset = self.before_filters(queryset, data)
        for name, value in six.iteritems(data):
            if name not in allowed or value in (None, '', [], ()):
                continue
            kwargs = {}
            field = self.fields[name]
            if hasattr(self, "filter_%s" % name):
                result = getattr(self, "filter_%s" % name)(queryset, value, data)
            elif hasattr(field, "filter_queryset"):
                result = field.filter_queryset(queryset, value, self[name])
            else:
                if isinstance(value, (tuple,list)):
                    name = '%s__in' % name
                kwargs[name] = value
                result = queryset.filter(**kwargs)
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
    pass


class TableSortField(GingerSortField):

    def __init__(self, table_class, **kwargs):
        column_dict = OrderedDict(Formatter.extract_from(table_class))
        self.reverse = kwargs.pop("reverse", False)
        choices = [(name, col.label or name.title()) for name, col in six.iteritems(column_dict) if not col.hidden]
        super(TableSortField, self).__init__(choices=choices, **kwargs)
        self.table_class = table_class

    def handle_queryset(self, queryset, value, bound_field):
        text_value = force_text(value) if value is not None else None
        if not text_value:
            return queryset
        reverse = text_value.startswith("-")
        column_dict = self.table_class.get_column_dict()
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


def action_model_factory(model_class, include=None, exclude=(), **kwargs):
    name = "%sActionForm" % model_class.__name__
    meta = type("Meta", (), {"include": include, "exclude": exclude, "model": model_class})
    kwargs['Meta'] = meta
    return type(name, (ActionModelForm, ), kwargs)