
import inspect
import functools

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse, path
from django.http.response import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls.exceptions import NoReverseMatch

from djingles.formatters.models import object_formatter_factory, table_formatter_factory
from djingles.forms import action_model_form_factory
from djingles.views.generic import CommonFormView, CommonTemplateView

from djingles.pagination import Paginator


__all__ = [
           'CommonViewSet',
           'CreateViewSetMixin',
           'CommonModelViewSet',
           'UpdateViewSetMixin',
           'ListViewSetMixin',
           'DeleteViewSetMixin',
           'DetailViewSetMixin',
            'CloneViewSetMixin',
            'detail_view',
            'list_view'
           ]


class _SubView(object):
    detail = False
    regex = None
    methods = None

    def __init__(self, name, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
        self.name = name


def view(**kwargs):
    methods = kwargs.pop("methods", None)

    def wrapper(func):
        subview = _SubView(name=func.__name__, **kwargs)
        wrapped = func
        if methods:
            def closure(self, request, *args, **kw):
                if methods and request.method not in methods:
                    return HttpResponseNotAllowed(request.method)
                response = func(self, request, *args, **kw)
                return response
            wrapped = functools.update_wrapper(closure, func)

        wrapped.__subview__ = subview
        return func

    return wrapper


def list_view(**kwargs):
    kwargs['detail'] = False
    return view(**kwargs)


def detail_view(**kwargs):
    kwargs['detail'] = True
    return view(**kwargs)


def get_child_views(cls):
    for name, func in inspect.getmembers(cls):
        if callable(func) and hasattr(func, '__subview__'):
            yield func.__subview__


class ViewSetMixin:

    action = None
    base_name = None
    url_name = None
    url_regex = None

    def check_object_permissions(self, obj):
        pass

    def check_permissions(self):
        pass

    def get_template_names(self):
        template_name = self.template_name
        return [template_name.format(action=self.action)]

    def reverse(self, action_name, **kwargs):
        url_name = "%s_%s" % (self.base_name, action_name)
        return reverse(url_name, kwargs=kwargs)

    def get(self, request, *args, **kwargs):
        self.check_permissions()
        return getattr(self, self.action)(request)

    def post(self, request, *args, **kwargs):
        self.check_permissions()
        return getattr(self, self.action)(request)

    def process_response(self, request, response):
        if isinstance(response, dict):
            response = self.render_to_response(self.get_context_data(**response))
        return response

    @classmethod
    def get_action_list(cls):
        for name, func in inspect.getmembers(cls):
            if callable(func) and hasattr(func, '__subview__'):
                yield func.__subview__

    @classmethod
    def as_urls(cls, base_name, url_name=None, **kwargs):
        result = []
        # if url_name is None:
        #     url_name = base_name
        for subview in cls.get_action_list():
            action = subview.name
            segments = [url_name] if url_name else []
            if subview.detail:
                segments.append("<int:object_id>")
            if subview.regex is not None:
                regex = subview.regex
            else:
                regex = action
            if regex:
                segments.append(regex)
            segments.append("")
            view_url_name = "%s_%s" % (base_name, action)
            url_regex = "/".join(segments)
            view_class = path(url_regex, cls.as_view(
                base_name=base_name,
                action=subview.name,
                url_name=view_url_name,
                url_regex=url_regex,
                **kwargs
            ), name=view_url_name)
            result.append(view_class)
        return result


class DetailViewSetMixin(object):

    @view(detail=True, regex="")
    def detail(self, request):
        self.object = self.get_object()
        ctx = {
            self.context_object_key: self.object
        }
        object_formatter = self.get_object_formatter()
        if object_formatter:
            ctx[self.context_formatted_object_key] = object_formatter(self.object, variant="detail")
        context = self.get_context_data(**ctx)
        return self.render_to_response(context)


class CreateViewSetMixin(object):

    @view()
    def create(self, request):
        return self.handle_object_form()


class UpdateViewSetMixin(object):

    @view(detail=True)
    def update(self, request):
        self.object = self.get_object()
        return self.handle_object_form()


class DeleteViewSetMixin(object):

    @view(detail=True)
    def delete(self, request):
        self.object = self.get_object()
        return self.handle_object_form()


class CloneViewSetMixin(object):

    @view(detail=True)
    def clone(self, request):
        self.object = self.get_object()
        self.success_url = self.reverse("list")
        return self.handle_object_action()


class ListViewSetMixin(object):

    context_page_key = 'object_list_page'
    context_order_key = 'order'

    @view(regex="")
    def list(self, request):
        object_list_formatter = self.get_object_list_formatter()

        object_list = self.filter_queryset(self.get_queryset(), formatter_class=object_list_formatter)

        filter_form = self.filter_form

        ctx = {}

        object_list = self.paginate_queryset(object_list)

        ctx[self.context_page_key] = object_list

        if object_list_formatter:
            object_list = object_list_formatter(object_list,
                                                sort_key=self.context_order_key,
                                                sort_field=filter_form.fields.get(self.context_order_key) if filter_form else None)

        ctx[self.context_object_list_key] = object_list

        ctx['filter_form'] = self.filter_form

        return self.render_to_response(self.get_context_data(**ctx))


class CommonViewSet(ViewSetMixin, CommonTemplateView):
    pass


class CommonModelViewSet(ViewSetMixin, CommonFormView):

    filter_class = None

    object_formatter = None
    object_list_formatter = None
    action_fields = None

    paginator = Paginator
    url_object_key = 'object_id'
    context_object_key = 'object'
    context_object_list_key = 'object_list'
    context_formatted_object_key = 'formatted_object'
    object_formatter_fields = None
    object_list_formatter_fields = None
    params_page_key = 'page'
    per_page = None

    OK_BACK = 1
    YES_BACK = 2
    CONFIRM_BACK = 3
    SUBMIT_BACK = 4

    def __init__(self, *args, **kwargs):
        super(CommonModelViewSet, self).__init__(*args, **kwargs)
        self.extra_context = {}
        self.form_context = {}
        self.form_initial = {}
        self.form_instance = None
        self.filter_form = None

    def render_to_response(self, ctx, **response_kwargs):
        self.extra_context.update(ctx)
        return super(CommonModelViewSet, self).render_to_response(self.extra_context, **response_kwargs)

    def get_queryset(self):
        return self.queryset

    def filter_queryset(self, queryset, **kwargs):
        self.filter_form = self.get_filter_form(**kwargs)
        if self.filter_form:
            queryset = self.filter_form.perform_filter(queryset)
        return queryset

    def get_filter_kwargs(self):
        return {
            "initial": self.get_filter_initial(),
            "data": self.request.GET,
            "files": None,
            "context": {"request": self.request, "user": self.user}
        }

    def get_object_formatter(self):
        if self.object_formatter is None:
            model_class = self.get_queryset().model
            self.object_formatter = object_formatter_factory(
                model_class,
                fields=self.object_formatter_fields
            )
        return self.object_formatter

    def get_object_list_formatter(self):
        if self.object_list_formatter is None:
            model_class = self.get_queryset().model
            self.object_list_formatter = table_formatter_factory(
                model_class,
                fields=self.object_list_formatter_fields,
                get_cell_url=lambda me, cell: cell.source.get_absolute_url() if
                        hasattr(cell.source, 'get_absolute_url') else self.reverse("detail", object_id=cell.source.id)
            )
        return self.object_list_formatter

    def get_form_class(self, form_key=None):
        form_class = super(CommonModelViewSet, self).get_form_class(form_key)
        if form_class is None:
            model_class = self.get_queryset().model
            form_class = action_model_form_factory(model_class, include=self.action_fields)
        return form_class

    def get_filter_initial(self):
        return None

    def get_filter_form(self, **extra):
        filter_class = self.get_filter_class()
        if filter_class:
            kwargs = self.get_filter_kwargs()
            kwargs["context"].update(extra)
            return filter_class(**kwargs)

    def paginate_queryset(self, queryset, per_page=None, params_page_key=None):
        if per_page is None:
            per_page = self.per_page
        if params_page_key is None:
            params_page_key = self.params_page_key
        if not per_page:
            return queryset
        return self.paginator(
            queryset,
            per_page=per_page,
            parameter_name=params_page_key,
            allow_empty=False
        ).page(self.request)

    def get_object(self):
        queryset = self.get_queryset()
        try:
            obj = queryset.get(pk=self.kwargs[self.url_object_key])
            self.check_object_permissions(obj)
            return obj
        except queryset.model.DoesNotExist:
            raise Http404

    def get_form_action(self):
        return self.action

    def get_form_context(self, form_key):
        ctx = super(CommonModelViewSet, self).get_form_context(form_key)
        ctx['request'] = self.request
        ctx['action'] = self.get_form_action()
        ctx.update(self.form_context)
        return ctx

    def get_form_initial(self, form_key):
        initial = super(CommonModelViewSet, self).get_form_initial(form_key) or {}
        initial.update(self.form_initial)
        return initial

    def get_form_instance(self, form_key):
        form_instance = self.form_instance
        return form_instance if form_instance is not None else getattr(self, self.context_object_key, None)

    def get_filter_class(self):
        return self.filter_class

    def render_context(self, context):
        return self.render_to_response(self.get_context_data(**context))

    def handle_object_action(self, **kwargs):
        if not hasattr(self, 'object'):
            self.object = self.get_object()
        return self.handle_object_form(**kwargs)

    def handle_object_form(self, **kwargs):
        request = self.request
        method = request.method
        self.extra_context.update(kwargs)
        if method == 'GET':
            form = self.get_form(None, data=None, files=None)
            return self.render_form(form)
        else:
            try:
                if self.success_url is None:
                    if self.action in {'delete', "create"}:
                        self.success_url = self.reverse('list')
                    else:
                        self.success_url = self.reverse('detail', object_id=self.object.id)
            except NoReverseMatch:
                pass
            return self.process_submit(None, data=request.POST, files=request.FILES)

    def handle_queryset_action(self):
        request = self.request
        method = request.method
        if method == 'GET':
            return HttpResponse("Bad Request", status=400)
        else:
            object_list = self.get_queryset()
            form = self.filter_class(queryset=object_list, action=self.action, data=request.GET)
            if form.is_valid():
                return redirect(self.get_success_url(form))
            else:
                return redirect(self.get_previous_url())


