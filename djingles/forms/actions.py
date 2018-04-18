
import datetime
import inspect
from django.core.exceptions import ImproperlyConfigured
from django.http.request import QueryDict
from django.utils import six
from django import forms
from django.core.paginator import Page

from ginger.exceptions import ValidationFailure
from ginger import utils, paginator
from ginger import html
import warnings


__all__ = ['GingerModelForm', 
           'GingerForm',
           'GingerSearchModelForm',
           'GingerSearchForm',
           'GingerSafeEmptyTuple',
           'GingerFormMixin',
           'GingerSearchFormMixin',
           'GingerDataForm',
           'GingerDataModelForm',
           'GingerModelFormSet']



class GingerSafeEmptyTuple(tuple):
    def __len__(self):
        return 1

class GingerFormMixinBase(object):
    failure_message = None
    success_message = None
    confirmation_message = None

    def __init__(self, **kwargs):
        parent_cls = forms.Form if not isinstance(self, forms.ModelForm) else forms.ModelForm
        constructor = parent_cls.__init__
        keywords = set(inspect.getargspec(constructor).args)
        context = {}
        for key in kwargs.copy():
            if key in keywords:
                continue
            value = kwargs.pop(key)
            context[key] = value
        super(GingerFormMixinBase, self).__init__(**kwargs)
        self.context = context

    @property
    def result(self):
        self.is_valid()
        return self.__result

    def get_success_message(self):
        return self.success_message

    def get_failure_message(self):
        return self.failure_message

    def get_confirmation_message(self):
        return self.confirmation_message

    @classmethod
    def class_oid(cls):
        """
        Obfuscated class id
        :return: str
        """
        return utils.create_hash(utils.qualified_name(cls).encode('utf-8'))

    def process_context(self):
        context = self.context.copy()
        if hasattr(self, "cleaned_data"):
            if hasattr(self, "save"):
                instance = self.save(commit=False)
                context["instance"] = instance
            context["data"] = self.cleaned_data
        spec = inspect.getargspec(self.execute)
        if spec.varargs:
            raise ImproperlyConfigured("Form.execute cannot have variable arguments")
        if spec.keywords:
            return context
        return {k: context[k] for k in spec.args[1:] if k in context}


    def full_clean(self):
        super(GingerFormMixinBase, self).full_clean()
        try:
            _ = self.__result
        except AttributeError:
            result = None
            try:
                if self.is_bound :
                    context = self.process_context()
                    result = self.execute(**context)
            except forms.ValidationError as ex:
                self.add_error(None, ex)
            finally:
                self.__result = result

    def execute(self, **kwargs):
        return {}

    @classmethod
    def is_submitted(cls, data):
        return data and (any(k in data for k in cls.base_fields) or cls.submit_name() in data)

    @classmethod
    def submit_name(cls):
        return "submit-%s" % cls.class_oid()


class GingerFormMixin(object):

    failure_message = None
    success_message = None
    confirmation_message = None
    ignore_errors = False
    use_defaults = False
    template_name = None

    def __init__(self, **kwargs):
        parent_cls = forms.Form if not isinstance(self, forms.ModelForm) else forms.ModelForm
        constructor = parent_cls.__init__
        parent_constructor = super(GingerFormMixin, self).__init__
        keywords = set(inspect.getargspec(constructor).args)
        func = lambda a: getattr(a, 'im_func', a)
        parent_keywords = set(inspect.getargspec(parent_constructor).args) \
            if func(parent_constructor) is not func(constructor) else set()
        self.use_defaults = kwargs.pop("use_defaults", self.use_defaults)
        if "ignore_errors" in kwargs:
            self.ignore_errors = kwargs.pop("ignore_errors")
        context = {}
        for key in kwargs.copy():
            if key in keywords and key not in parent_keywords:
                continue
            value = kwargs.pop(key) if key not in parent_keywords else kwargs.get(key)
            context[key] = value
        super(GingerFormMixin, self).__init__(**kwargs)
        self.context = context
        self.merge_defaults()

    def get_template_names(self):
        template_name = self.template_name
        if not template_name:
            raise ImproperlyConfigured("Not template defined for this form")
        return [template_name]

    def insert_null(self, field_name, label, initial=""):
        field = self.fields[field_name]
        if initial is None:
            initial = field.empty_value
        field.required = False
        field.initial = initial
        choices = list(field.choices)
        top = choices[0][0]
        if top == field.empty_value or not top:
            choices = choices[1:]
        choices.insert(0, (initial, label))
        field.choices = tuple(choices)

    def _bind_fields(self):
        key = "__bound_with_form"
        for field in self.fields.values():
            if hasattr(field, 'bind_form') and not getattr(field, key, False):
                setattr(field, key, True)
                field.bind_form(self)

    def field_range(self, first, last=None, step=None):
        return html.field_range(self, first, last, step, hidden=True)

    def iter_fields(self, names):
        return (self[field] for field in names)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self.field_range(item.start, item.stop, item.step)
        return super(GingerFormMixin, self).__getitem__(item)

    def merge_defaults(self):
        if self.use_defaults:
            data = QueryDict('', mutable=True)
            if self.data:
                data.update(self.data)
            initial = self.initial_data
            for key in initial:
                if key in data:
                    continue
                value = initial[key]
                name = self.add_prefix(key)
                if value is not None:
                    if isinstance(value, (list, tuple)):
                        data.setlistdefault(name, value)
                    else:
                        data.setdefault(name, value)
            self.data = data

    def process_context(self):
        context = self.context.copy()
        if not isinstance(self, GingerSearchFormMixin) and hasattr(self, "cleaned_data"):
            if hasattr(self, "save"):
                instance = self.save(commit=False)
                context["instance"] = instance
            context["data"] = self.cleaned_data
        spec = inspect.getargspec(self.execute)
        if spec.varargs:
            raise ImproperlyConfigured("Form.execute cannot have variable arguments")
        if spec.keywords:
            return context
        return {k: context[k] for k in spec.args[1:] if k in context}

    @property
    def initial_data(self):
        fields = self.fields
        result = {}
        for name,field in six.iteritems(fields):
            data = self.initial.get(name, field.initial)
            if callable(data):
                data = data()
                if (isinstance(data, (datetime.datetime, datetime.time)) and
                        not getattr(field.widget, 'supports_microseconds', True)):
                    data = data.replace(microsecond=0)
            if data and isinstance(field, forms.MultiValueField):
                for i, f in enumerate(field.fields):
                    key = "%s_%s" % (name, i)
                    result[key] = data[i]
            elif data is not None:
                result[name] = data
        return result

    @property
    def result(self):
        self.is_valid()
        return self.__result

    def get_success_message(self):
        return self.success_message

    def get_failure_message(self):
        return self.failure_message

    def get_confirmation_message(self):
        return self.confirmation_message

    @classmethod
    def class_oid(cls):
        """
        Obfuscated class id
        :return: str
        """
        return utils.create_hash(utils.qualified_name(cls))

    @classmethod
    def is_submitted(cls, data):
        return data and (any(k in data for k in cls.base_fields) or cls.submit_name() in data)

    @classmethod
    def submit_name(cls):
        return "submit-%s" % cls.class_oid()

    def run(self):
        if not self.is_valid() and not self.ignore_errors:
            raise ValidationFailure(self)
        return self.result

    def full_clean(self):
        super(GingerFormMixin, self).full_clean()
        try:
            _ = self.__result
        except AttributeError:
            result = None
            try:
                self._bind_fields()
                if self.is_bound and (not self._errors or self.ignore_errors):
                    context = self.process_context()
                    result = self.execute(**context)
            except forms.ValidationError as ex:
                self.add_error(None, ex)
            finally:
                self.__result = result

    def execute(self, **kwargs):
        return {}

    def as_html(self):
        return html

    def to_json(self):
        return {
            'message': self.get_success_message(),
            'data': self.run()
        }


class GingerModelForm(GingerFormMixin, forms.ModelForm):
    pass

class GingerForm(GingerFormMixin, forms.Form):
    pass


class GingerSearchFormMixin(GingerFormMixin):

    per_page = 20
    page_limit = 10
    parameter_name = "page"
    ignore_errors = True
    use_defaults = True

    def _post_clean(self):
        """
            This override is needed so as to avoid modelform validation during clean
        """

    def get_sort_field(self):
        from .fields import GingerSortField
        try:
            return next(self[name] for name, f in six.iteritems(self.fields) if isinstance(f, GingerSortField))
        except StopIteration:
            return None

    def get_queryset(self, **kwargs):
        queryset = self.context.get("queryset")
        if queryset is not None:
            return queryset
        return self.queryset

    def execute(self, **kwargs):
        return self.process_queryset_filters(**kwargs)

    def get_queryset_filter_names(self):
        return self.fields.keys()

    def process_queryset_filters(self, page=None, parameter_name="page",
                      page_limit=10, per_page=20, **kwargs):
        queryset = self.get_queryset(**kwargs)
        data = self.cleaned_data if self.is_bound else self.initial_data
        allowed = set(self.get_queryset_filter_names())
        if hasattr(self, "before_filters"):
            queryset = self.before_filters(queryset, data)
        for name, value in six.iteritems(data):
            if name not in allowed or value in (None, '', [], ()):
                continue
            kwargs = {}
            field = self.fields[name]
            if hasattr(self, "filter_%s" % name):
                result = getattr(self, "filter_%s" % name)(queryset, value, data)
            elif hasattr(self, "handle_%s" % name):
                result = getattr(self,"handle_%s" % name)(queryset, value, data)
            elif hasattr(field, "handle_queryset"):
                result = field.handle_queryset(queryset, value, self[name])
            else:
                if isinstance(value, (tuple,list)):
                    name = '%s__in' % name
                kwargs[name] = value
                result = queryset.filter(**kwargs)
            if result is not None:
                queryset = result
        if hasattr(self, "after_filters"):
            queryset = self.after_filters(queryset, data)
        if page is not None:
            queryset = self.paginate(queryset, page,
                                 parameter_name=parameter_name,
                                 page_limit=page_limit, per_page=per_page)
        return queryset

    @staticmethod
    def paginate(object_list, page, **kwargs):
        return paginator.paginate(object_list, page, **kwargs)

    def is_paginated(self):
        return 'page' in self.context

    def to_json(self):
        warnings.warn("Form.to_json is deprecated and shall be removed in ginger 1.0", DeprecationWarning)
        result = self.run()
        if isinstance(result, Page):
            return {
                'data': result.object_list,
                'page': result
            }
        else:
            return {
                'data': result
            }


class GingerSearchModelForm(GingerSearchFormMixin, forms.ModelForm):
    pass


class GingerSearchForm(GingerSearchFormMixin, forms.Form):
    pass


class GingerDataFormMixin(GingerSearchFormMixin):

    def execute(self, **kwargs):
        result = super(GingerDataFormMixin, self).execute(**kwargs)
        schema_cls = self.get_dataset_class()
        dataset = schema_cls()
        self.load_dataset(dataset, result)
        self.process_dataset_filters(dataset)
        return dataset

    def load_dataset(self, dataset, data_source):
        dataset.extend(data_source)

    def process_dataset_filters(self, dataset, **kwargs):
        cleaned_data = self.cleaned_data if self.is_bound else self.initial_data
        for name in self.get_dataset_filter_names():
            value = cleaned_data.get(name)
            field = self.fields.get(name)
            if value is None or value == "":
                continue
            if hasattr(self, "handle_%s" % name):
                getattr(self,"handle_%s" % name)(dataset, value, cleaned_data)
            elif field and hasattr(field, "handle_dataset"):
                field.handle_dataset(dataset, value, self[name])
        sort_field = self.get_sort_field()
        if sort_field:
            dataset.sort_parameter_name = sort_field.html_name
            dataset.sort_field = sort_field.field
        return dataset

    def get_dataset_class(self):
        try:
            return next(f.dataset_class for f in six.itervalues(self.fields)
                        if hasattr(f, "dataset_class"))
        except StopIteration:
            return self.dataset_class

    def get_dataset_filter_names(self):
        names = set(name for name, f in six.iteritems(self.fields)
                    if getattr(f, "process_list", False))
        names.update(getattr(self, "dataset_filters", ()))
        return names

    def get_queryset_filter_names(self):
        names = super(GingerDataFormMixin, self).get_queryset_filter_names()
        dataset_filters = set(self.get_dataset_filter_names())
        return [name for name in names if name not in dataset_filters]

    def to_json(self):
        result = self.run()
        return {
            "data": result.rows,
            "aggregates": result.aggregates.rows,
            "page": result.object_list if result.is_paginated() else None,
            "schema": [col.to_json() for col in result.columns]
        }


class GingerDataModelForm(GingerDataFormMixin, forms.ModelForm):
    pass


class GingerDataForm(GingerDataFormMixin, forms.Form):
    pass


class GingerModelFormSet(forms.BaseModelFormSet):
    failure_message = None
    success_message = None
    confirmation_message = None

    def __init__(self, **kwargs):
        parent_cls = forms.BaseFormSet if not isinstance(self, forms.BaseModelFormSet) else forms.BaseModelFormSet
        constructor = parent_cls.__init__
        keywords = set(inspect.getargspec(constructor).args)
        context = {}
        for key in kwargs.copy():
            if key in keywords:
                continue
            value = kwargs.pop(key)
            context[key] = value
        super(GingerModelFormSet, self).__init__(**kwargs)
        self.context = context

    @property
    def result(self):
        self.is_valid()
        return self.__result

    def get_success_message(self):
        return self.success_message

    def get_failure_message(self):
        return self.failure_message

    def get_confirmation_message(self):
        return self.confirmation_message

    @classmethod
    def class_oid(cls):
        """
        Obfuscated class id
        :return: str
        """
        return utils.create_hash(utils.qualified_name(cls).encode('utf-8'))

    def process_context(self):
        context = self.context.copy()
        if hasattr(self, "cleaned_data"):
            if hasattr(self, "save"):
                instance = self.save(commit=False)
                context["instance"] = instance
            context["data"] = self.cleaned_data
        spec = inspect.getargspec(self.execute)
        if spec.varargs:
            raise ImproperlyConfigured("Form.execute cannot have variable arguments")
        if spec.keywords:
            return context
        return {k: context[k] for k in spec.args[1:] if k in context}


    def full_clean(self):
        super(GingerModelFormSet, self).full_clean()
        try:
            _ = self.__result
        except AttributeError:
            result = None
            try:
                if self.is_bound and not any(self._errors) and not self._non_form_errors:
                    context = self.process_context()
                    result = self.execute(**context)
            except forms.ValidationError as ex:
                self.add_error(None, ex)
            finally:
                self.__result = result

    def execute(self, **kwargs):
        return {}

    @classmethod
    def is_submitted(cls, data):
        return data and (any(k in data for k in cls.base_fields) or cls.submit_name() in data)

    @classmethod
    def submit_name(cls):
        return "submit-%s" % cls.class_oid()

    def add_error(self, name, errors):
        if name is None:
            self._non_form_errors.append(errors)