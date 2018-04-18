

from djingles.bootstrap4 import forms, models
from django.views import generic


class VerticalFormView(generic.FormView):
    template_name = "bootstrap4/form.html"
    form_class = forms.VerticalForm


class InlineFormView(generic.FormView):
    template_name = "bootstrap4/inline_form.html"
    form_class = forms.InlineForm


class ObjectTable(generic.ListView):
    pass


class ObjectDetailView(generic.DetailView):
    pass


class ObjectEditView(generic.UpdateView):
    pass


class ObjectDeleteView(generic.DeleteView):
    pass


class ObjectCreateView(generic.CreateView):
    pass