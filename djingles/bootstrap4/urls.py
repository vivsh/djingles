
from django.urls import path
from djingles.bootstrap4 import views


urlpatterns = [
    path("form/", views.VerticalFormView.as_view()),
    path("filters/", views.InlineFormView.as_view()),
]
