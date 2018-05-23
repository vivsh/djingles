

from django import forms
from django.contrib import messages
from django.forms.models import ModelForm
from django.shortcuts import redirect
from django.views.generic.base import TemplateResponseMixin, View
from djingles import utils, exceptions


__all__ = ['CommonView', 'CommonSessionDataMixin', 'CommonTemplateView', 'CommonFormView']


class CommonSessionDataMixin(object):

    session_key_prefix = ""

    def get_session_key(self):
        return "%s-%s" % (self.session_key_prefix, self.class_oid())

    def get_session_data(self):
        return self.request.session.get(self.get_session_key())

    def set_session_data(self, data):
        self.request.session[self.get_session_key()] = data

    def clear_session_data(self):
        self.request.session.pop(self.get_session_key(), None)

    @classmethod
    def class_oid(cls):
        return utils.create_hash(utils.qualified_name(cls))


class CommonView(View, CommonSessionDataMixin):

    DEBUG = messages.DEBUG
    INFO = messages.INFO
    WARNING = messages.WARNING
    ERROR = messages.ERROR
    SUCCESS = messages.SUCCESS

    def get_user(self):
        return self.request.user

    def process_request(self, request):
        self.user = self.get_user()

    def process_response(self, request, response):
        return response

    def process_exception(self, request, ex):
        if isinstance(ex, exceptions.Redirect):
            return redirect(ex.create_url(request), permanent=ex.permanent)

    def dispatch(self, request, *args, **kwargs):
        try:
            response = self.process_request(request)
            if not response:
                response = super(CommonView, self).dispatch(request, *args, **kwargs)
        except Exception as ex:
            response = self.process_exception(request, ex)
            if response is None:
                raise
        response = self.process_response(request, response)
        return response

    def get_context_data(self, **kwargs):
        if 'view' not in kwargs:
            kwargs['view'] = self
        return kwargs

    def add_message(self,  message, level=messages.INFO, **kwargs):
        if not message:
            return
        messages.add_message(self.request, level, message, **kwargs)

    def get_messages(self):
        return messages.get_messages(self.request)

    def get_previous_url(self, default="/"):
        return self.request.META.get("HTTP_REFERER", default)


class CommonTemplateView(CommonView, TemplateResponseMixin):

    view_icon = None

    view_label = None

    page_title = None

    page_heading = None

    page_actions = ()

    page_css_class = None

    def __init__(self, **kwargs):
        super(CommonTemplateView, self).__init__(**kwargs)
        self.extra_context = {}

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_page_css_class(self):
        return self.page_css_class

    def get_page_title(self):
        return self.page_title or self.get_page_heading()

    def get_page_heading(self):
        return self.page_heading

    def get_page_actions(self):
        return self.page_actions

    def get_view_icon(self):
        return self.view_icon

    def get_view_label(self):
        return self.view_label

    def render_to_response(self, ctx, **response_kwargs):
        ctx.update(self.extra_context)
        if not self.request.is_ajax():
            ctx['view'] = self
            ctx.setdefault("messages", self.get_messages())
            ctx.setdefault('page_heading', self.get_page_heading())
            ctx.setdefault('page_title', self.get_page_title())
            ctx.setdefault('page_actions', self.get_page_actions())
            ctx.setdefault('page_css_class', self.get_page_css_class())
        response = super(CommonTemplateView, self).render_to_response(ctx, **response_kwargs)
        return response


class CommonFormView(CommonTemplateView):

    success_url = None
    form_class = None

    context_form_key = "form"

    def get_context_form_key(self, form):
        key = self.context_form_key or "form"
        return key

    def get_success_url(self, form):
        return self.success_url

    def get_form_class(self, form_key=None):
        return self.form_class

    def get_form_key(self):
        return

    def can_submit(self):
        return self.request.method == "POST"

    def post(self, request, *args, **kwargs):
        if self.can_submit():
            return self.process_submit(
                form_key=self.get_form_key(),
                data=request.POST,
                files=request.FILES
            )
        return redirect(request.get_full_path())

    def get(self, request, *args, **kwargs):
        form_key = self.get_form_key()
        if self.can_submit():
            return self.process_submit(form_key=form_key, data=request.GET)
        else:
            data, files = self.get_form_data(form_key)
            form = self.get_form(form_key=form_key, data=data, files=files)
            return self.render_form(form)

    def get_form_data(self, form_key):
        return None, None

    def set_form_data(self, form_key, data, files=None):
        raise NotImplementedError

    def form_valid(self, form):
        url = self.get_success_url(form)
        msg = form.get_success_message()
        self.add_message(level=messages.SUCCESS, message=msg)
        return redirect(url) if not callable(url) else url(form)

    def form_invalid(self, form):
        msg = form.get_failure_message()
        self.add_message(level=messages.ERROR, message=msg)
        return self.render_form(form)

    def render_form(self, form):
        form_key = self.get_form_key()
        kwargs = {self.get_context_form_key(form_key): form}
        return self.render_to_response(self.get_context_data(**kwargs))

    def get_form_initial(self, form_key):
        return None

    def get_form_prefix(self, form_key):
        return None

    def get_form_instance(self, form_key):
        return None

    def get_form_context(self, form_key):
        action = self.action
        ctx = {
            "request": self.request,
            "user": self.user,
        }
        if action:
            ctx['action'] = action
        return ctx

    def get_form_kwargs(self, form_key):
        kwargs = {
            "initial": self.get_form_initial(form_key),
            "prefix": self.get_form_prefix(form_key),
        }
        form_class = self.get_form_class(form_key)
        if form_class and issubclass(form_class, ModelForm):
            kwargs['instance'] = self.get_form_instance(form_key)
        kwargs['context'] = self.get_form_context(form_key)
        return kwargs

    def process_submit(self, form_key, data=None, files=None):
        form_obj = self.get_form(form_key, data=data, files=files)
        if form_obj.is_valid():
            return self.form_valid(form_obj)
        else:
            return self.form_invalid(form_obj)

    def get_form(self, form_key, data=None, files=None):
        form_class = self.get_form_class(form_key)
        kwargs = self.get_form_kwargs(form_key)
        kwargs['data'] = data
        kwargs['files'] = files
        form_obj = form_class(**kwargs)
        return form_obj


class CommonMultipleFormView(CommonFormView):

    form_classes = {}
    form_key_parameter = '_fkey'

    def get_context_form_key(self, form_key):
        suffix = "form"
        return suffix if not form_key else "%s_%s" % (form_key, suffix)

    def get_form_key(self):
        if not self.can_submit():
            return None
        name = self.form_key_parameter
        request = self.request
        data = request.GET if request.method == 'GET' else request.POST
        for key in self.form_classes:
            field_name = '%s-%s' % (key, name)
            if field_name in data:
                return data[field_name]

    def get_form(self, form_key, data=None, files=None):
        form_obj = super(CommonMultipleFormView, self).get_form(form_key, data, files)
        form_obj.fields[self.form_key_parameter] = forms.CharField(widget=forms.HiddenInput, initial=form_key)
        return form_obj

    def get_form_prefix(self, form_key):
        return form_key

    def get_form_class(self, form_key):
        return self.form_classes[form_key]

    def get_unbound_form_keys(self):
        return [k for k in self.form_classes.keys() if k != self.get_form_key()]

    def get(self, request, *args, **kwargs):
        key = self.get_form_key()
        if key is None:
            context = self.get_context_data(**kwargs)
            return self.render_to_response(context)
        return self.process_submit(key, data=request.GET, files=None)

    def post(self, request, *args, **kwargs):
        key = self.get_form_key()
        if key is None:
            return redirect(request.get_full_path())
        return self.process_submit(key, data=request.POST, files=request.FILES)

    def get_context_data(self, **kwargs):
        context = super(CommonMultipleFormView, self).get_context_data(**kwargs)
        for form_key in self.get_unbound_form_keys():
            data, files = self.get_form_data(form_key)
            form = self.get_form(form_key=form_key, data=data, files=files)
            context[self.get_context_form_key(form_key)] = form
        return context
