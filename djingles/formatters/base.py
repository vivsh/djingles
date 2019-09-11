
from jinja2 import Markup
import inspect
import copy
from collections import OrderedDict, deque

from djingles.html import Link
from django.utils.formats import localize
from djingles.utils import url_query_update, flatten

__all__ = ['Formatter', 'FormattedTable', 'FormattedObject']


class Formatter(object):

    __position = 1

    def __init__(self, label=None, attr=None, hidden=False, sortable=True, reverse=False, empty="",
                 icon=None, url=None, editable=False, order_by=None):
        Formatter.__position += 1
        self.__position = Formatter.__position
        self.label = label
        self.icon = icon
        self.url = url
        self.hidden = hidden
        self.editable = editable
        self.sortable = sortable
        self.reverse = reverse
        self.attr = attr
        self.empty = empty
        self.order_by = order_by or self.attr

    def _update_position(self):
        Formatter.__position += 1
        self.__position = Formatter.__position

    def copy(self):
        instance = copy.copy(self)
        instance._update_position()
        return instance

    @property
    def position(self):
        return self.__position

    def format(self, value, name, source):
        value = localize(value)
        return str(value)

    def extract(self, name, source, owner=None):
        if owner is not None:
            method = 'prepare_%s' % name
            func = getattr(owner, method, None)
            if func:
                return func(source)
        if self.attr:
            name = self.attr
        parts = name.split("__")
        result = source
        while parts:
            item = parts.pop(0)
            if isinstance(result, dict):
                result = result[item]
            else:
                result = getattr(result, item)
            if result is None:
                break
        return result

    def render(self, name, source, owner):
        value = self.extract(name, source, owner)
        return self.format(value, name, source)

    @classmethod
    def extract_from(cls, source, include=None, exclude=None):
        result = sorted(inspect.getmembers(source, lambda a: isinstance(a, Formatter)),
            key=lambda p: p[1].position)
        if include:
            result = [p for p in result if p[0] in list(include)]
        if exclude:
            result = [p for p in result if p[0] not in set(exclude)]
        return result


class FormattedValue(object):

    def __init__(self, name, prop, source, attrs=None, owner=None):
        self.name = name
        self.prop = prop
        self.source = source
        self.__attrs = attrs
        self.__owner = owner

    @property
    def attrs(self):
        return self.__attrs(self) if self.__attrs else {}

    @property
    def label(self):
        label = self.prop.label
        return label if label is not None else self.name.replace("_", " ").title()

    @property
    def url(self):
        if not self.prop.url:
            try:
                func = self.__owner.get_cell_url
            except AttributeError:
                return None
            else:
                return func(self)
        if callable(self.prop.url):
            return self.prop.url(self)
        return self.prop.url

    @property
    def value(self):
        try:
            return self.prop.extract(self.name, self.source, self.__owner)
        except AttributeError as ex:
            raise ValueError("Error while accessing attribute %r in %r : %s" % (self.name, self.source, ex))

    def __getattr__(self, item):
        return getattr(self.prop, item)

    def wrap_content(self, content):
        prefix = self.__owner.get_prefix(self.name)
        if prefix:
            content = "%s %s" % (prefix, content)
        suffix = self.__owner.get_suffix(self.name)
        if suffix:
            content = "%s %s" % (content, suffix)
        return Markup(content)

    def to_html(self):
        return self.wrap_content(self.to_str)

    def to_str(self):
        value = self.value
        if value is None or value == "":
            return self.prop.empty
        result = self.prop.format(value, self.name, self.source)
        return str(result)

    def __str__(self):
        return self.to_str()


class MetaFormattedObject(type):

    def __init__(cls, name, bases, attrs):
        super(MetaFormattedObject, cls).__init__(name, bases, attrs)
        cls.base_formatters = tuple((k, v) for k, v in Formatter.extract_from(cls))

    def subset_class(cls, include=None, exclude=None):
        name = "_Sub%s" % cls.__name__
        fields = Formatter.extract_from(cls, include=include, exclude=exclude)
        class_ = type(name, (cls, ), OrderedDict((k, v) for k, v in fields))
        return class_


class FormattedObject(metaclass=MetaFormattedObject):

    def __init__(self, obj, **context):
        self.context = context
        self.source = obj
        self.formatters = OrderedDict((k, v.copy()) for k,v in self.base_formatters)
        data = self.data = OrderedDict()
        for name, prop in self.formatters.items():
            data[name] = FormattedValue(name, prop, self.source, attrs=self.get_attrs, owner=self)

    def to_dict(self):
        return {c.name: str(c) for c in self}

    #This comes useful inside the templates when a single object has to be split into multiple fields
    def select(self, *names):
        stack = deque(names)
        while stack:
            item = stack.popleft()
            if isinstance(item, (list, tuple)):
                stack.extendleft(reversed(item))
            elif item in self.formatters:
                value = self[item]
                if not value.hidden:
                    yield self[item]

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __getitem__(self, item):
        try:
            return self.data[item]
        except KeyError:
            raise AttributeError(item)

    def __iter__(self):
        for name, prop in self.formatters.items():
            yield self.data[name]

    def __len__(self):
        return len(self.formatters)

    def __bool__(self):
        return len(self) > 0

    def get_attrs(self, value):
        return {}

    @classmethod
    def as_table(cls):
        props = dict(Formatter.extract_from(cls))
        for key, value in cls.__dict__.items():
            if not key.startswith("_") and callable(value):
                props[key] = value
        name = cls.__name__
        return type("%sTable"%name, (FormattedTable,), props)

    def get_prefix(self, name):
        return

    def get_suffix(self, name):
        return


class FormattedTableColumn(object):

    __inited = False

    def __init__(self, name, prop, table):
        self.name = name
        self.prop = prop
        self.table = table
        self.__inited = True

    @property
    def label(self):
        return self.prop.label or self.name.capitalize()

    def __setattr__(self, key, value):
        if self.__inited and key not in self.__dict__:
            setattr(self.prop, key, value)
        else:
            self.__dict__[key] = value

    def __getattr__(self, item):
        return getattr(self.prop, item)

    def __getitem__(self, item):
        return getattr(self.prop, item)

    def values(self):
        for obj in self:
            yield obj.value

    def __iter__(self):
        for obj in self.table.source:
            yield FormattedValue(self.name, self.prop, obj, self.table.get_cell_attrs)

    def __len__(self):
        return len(self.table.source)

    def __bool__(self):
        return len(self) > 0


class FormattedTableColumnSet(object):

    def __init__(self, table):
        self.columns = OrderedDict((n, FormattedTableColumn(n, p.copy(), table)) for n, p in table.base_formatters)

    def visible_columns(self):
        return [col for col in self.columns.values() if not col.hidden]

    def hidden_columns(self):
        return [col for col in self.columns.values() if col.hidden]

    def keys(self):
        return self.columns.keys()

    def remove(self, name):
        return self.columns.pop(name, None)

    def select(self, *names):
        clone = copy.copy(self)
        for key in self.columns.keys():
            if key not in names:
                clone.columns.pop(key)
        return clone

    def __iter__(self):
        for value in self.columns.values():
            yield value

    def __contains__(self, item):
        return item in self.columns

    def __getitem__(self, item):
        return self.columns[item]

    def __getattr__(self, item):
        return self.columns[item]

    def __len__(self):
        return len(self.columns)

    def __bool__(self):
        return len(self) > 0


class FormattedTableRow(object):

    def __init__(self, index, source, table, kind=None):
        self.index = index
        self.source = source
        self.table = table
        self.kind = kind
        self.data = OrderedDict()
        for column in self.table.columns:
            self.data[column.name] = FormattedValue(column.name, column.prop, source,
                                                    attrs=self.table.get_cell_attrs,
                                                    owner=table)

    def __getitem__(self, item):
        return self.data[item]

    @property
    def object(self):
        return self.source

    @property
    def attrs(self):
        return self.table.get_row_attrs(self)

    def __iter__(self):
        for column in self.table.columns:
            yield self.data[column.name]

    def __len__(self):
        return len(self.table.columns)

    def __bool__(self):
        return len(self) > 0


class FooterRow:

    __inited = False

    def __init__(self, table, label):
        data = self.data = {}
        for column in table.columns:
            data[column.name] = None
        self.label = label
        self.__inited = True

    def __getattr__(self, item):
        return self.data[item] if item in self.data else None

    def __setattr__(self, key, value):
        if self.__inited:
            self.data[key] = value
        else:
            self.__dict__[key] = value

    def __iter__(self):
        return iter(self.data)

    def to_row(self):
        return self.data


class FormattedTable(metaclass=MetaFormattedObject):

    def __init__(self, source, **context):
        self.context = context
        self.columns = FormattedTableColumnSet(self)
        self.source = source
        self._footer_rows = []

    def select(self, *names):
        clone = copy.copy(self)
        names = list(flatten(names))
        clone.columns = self.columns.select(names)
        return clone

    def build_links(self, request, bound_field=None):
        data = request.GET if request else {}
        sort_key = bound_field.name if bound_field else None
        sort_field = bound_field.field if bound_field else None
        for col in self.columns.visible_columns():
            if sort_key and sort_field:
                field = sort_field
                code = field.get_value_for_name(col.name)
                value = data.get(sort_key, "")
                reverse = value.startswith("-")
                if reverse:
                    value = value[1:]
                is_active = code == value
                next_value = "-%s" % code if not reverse and is_active else code
                mods = {sort_key: next_value}
            else:
                is_active = False
                reverse = False
                mods = {}
            if request:
                url = url_query_update(request.build_absolute_uri(), mods) if mods else None
            else:
                url = None
            link = Link(content=col.label, url=url, is_active=is_active, reverse=reverse, sortable=col.sortable, column=col)
            yield link

    @property
    def object_list(self):
        return self.source

    def create_footer_row(self, label):
        row = FooterRow(self, label)
        self._footer_rows.append(row)
        return row

    @property
    def footer(self):
        index = 0
        for obj in self._footer_rows:
            yield FormattedTableRow(index, obj, self)
            index += 1

    def __iter__(self):
        index = 0
        for obj in self.source:
            yield FormattedTableRow(index, obj, self)
            index += 1

    def __len__(self):
        return len(self.source)

    def __bool__(self):
        return len(self) > 0

    def get_row_attrs(self, row):
        return {}

    def get_cell_attrs(self, cell):
        return {}

    def get_prefix(self, name):
        return

    def get_suffix(self, name):
        return
