from django.http.request import HttpRequest
from django.utils import six
from django.core.paginator import Page as DjangoPage, Paginator as DjangoPaginator, EmptyPage, PageNotAnInteger

from djingles import utils
from djingles import html


__all__ = ["Paginator", "Page"]


class Page(DjangoPage):

    def create_link(self, request, number):
        param = self.paginator.parameter_name
        url = utils.url_query_update(request.build_absolute_uri(), {param: number})
        return html.Link(url=url, content=six.text_type(number), is_active=number==self.number)

    def build_links(self, request):
        for i in utils.page_number_range(self.number,
                                      self.paginator.page_limit,
                                      self.paginator.num_pages):
            yield self.create_link(request, i)

    def previous_link(self, request):
        number = self.previous_page_number()
        return self.create_link(request, number)

    def next_link(self, request):
        number = self.next_page_number()
        return self.create_link(request, number)


class Paginator(DjangoPaginator):

    parameter_name = "page"
    page_limit = 10
    allow_empty = False

    def __init__(self, object_list, per_page, **kwargs):
        self.parameter_name = kwargs.pop("parameter_name", self.parameter_name)
        self.allow_empty = kwargs.pop("allow_empty", self.allow_empty)
        self.page_limit = kwargs.pop("page_limit", self.page_limit)
        super(Paginator, self).__init__(object_list, per_page, **kwargs)

    def page(self, value):
        """
        Returns a Page object for the given 1-based page number.
        """
        if isinstance(value, HttpRequest):
            value = value.GET.get(self.parameter_name, 1)
        elif isinstance(value, dict):
            value = value.get(self.parameter_name, 1)
        return super(Paginator, self).page(value)

    def _get_page(self, *args, **kwargs):
        return Page(*args, **kwargs)
