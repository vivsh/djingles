
from django import forms
from collections import deque
import itertools
from djingles import html
from django.utils.encoding import force_text


class AbstractThemedWidget(object):
    attr_names = ("attrs", "choices")
    extra_attrs = {}

    @classmethod
    def __cached_subclasses(cls):
        cache_name = "_%s__widget_classes" % cls.__name__
        result = getattr(cls, cache_name, None)
        if result is None:
            result = {}
            subs = deque([cls])
            while subs:
                child = subs.popleft()
                result[child.__name__] = child
                subs.extendleft(child.__subclasses__())
            setattr(cls, cache_name, result)
        return result

    @classmethod
    def __mutate(cls, field):
        subclasses = cls.__cached_subclasses()
        widget = field.field.widget
        widget_class = widget.__class__
        name = widget_class.__name__
        if hasattr(widget, 'render_field'):
            return widget
        if name in subclasses:
            child = subclasses[name]
            widget = child.__consume(field)
        return widget

    @classmethod
    def __consume(cls, field):
        widget = field.field.widget
        common = cls.attr_names
        init_args = {}
        for name in common:
            try:
                init_args[name] = getattr(widget, name)
            except AttributeError:
                pass
        widget = cls(**init_args)
        field.field.widget = widget
        return widget

    @classmethod
    def widget_to_html(cls, field, **kwargs):
        widget = cls.__mutate(field)
        if hasattr(widget, 'render_widget'):
            return widget.render_widget(field, **kwargs)
        else:
            instance = cls()
            return instance.render_widget(field, **kwargs)

    @classmethod
    def field_to_html(cls, field, layout, **kwargs):
        field.layout = layout
        original_widget = field.field.widget
        widget = cls.__mutate(field)
        if hasattr(widget, 'render_field'):
            return widget.render_field(field, layout, **kwargs)
        else:
            instance = cls()
            return instance.render_field(field, layout, **kwargs)

    @classmethod
    def form_attrs(cls, form, **kwargs):
        return kwargs

    def render_field(self, field, layout, **kwargs):
        for k in kwargs:
            setattr(field.field, k, kwargs[k])
        return str(field)

    def render_widget(self, field):
        return str(field)

    def build_attrs(self, *args, **kwargs):
        attrs = super(AbstractThemedWidget, self).build_attrs(*args, **kwargs)
        extra = getattr(self, 'extra_attrs', {}).copy()
        css = html.CssClassList()
        css.append(extra.pop("class", ""))
        css.append(attrs.pop("class", ""))
        attrs.update(extra)
        if css:
            attrs['class'] = str(css)
        return attrs

    def add_css_class(self, classes):
        css = html.CssClassList()
        css.append(self.attrs.pop("class", ""))
        css.append(classes)
        self.attrs['class'] = str(css)


class ChoiceWidgetMixin(object):

    input_type = "radio"

    def render_from_field(self, field):
        return field.as_widget(widget=self)

    def render_subwidget_wrapper(self, content):
        classes = []
        return html.li(class_=classes)[content]

    def render_subwidget(self, code, label, selected, attrs):
        return [
            html.input(type=self.input_type, checked=selected, value=code, **attrs),
            html.label(for_=attrs.get("id"))[label]
        ]

    def render_wrapper(self, content, attrs):
        return html.ul(**attrs)[content].render()

    def render(self, name, value, attrs=None, choices=(), **kwargs):
        if value is None:
            value = ''
        attrs = self.build_attrs(attrs, self.attrs)
        children = []
        id_ = attrs.get("id")
        for i, (code, label) in enumerate(itertools.chain(self.choices, choices)):
            selected = html.is_selected_choice(value, code)
            child_attrs = attrs.copy()
            child_attrs.pop("class", None)
            if id_:
                child_attrs['id'] = "%s-%s" % (id_, i)
            child = self.render_subwidget(code, label, selected, child_attrs)
            children.append(self.render_subwidget_wrapper(child))
        return self.render_wrapper("".join(force_text(child) for child in children), attrs)


