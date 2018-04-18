

from django import forms
from djingles.bootstrap4.forms.widgets import SwitchInput


class InlineForm(forms.Form):

    CHOICES = (
        (1, "One"),
        (2, "Two"),
        (3, "Three"),
        (4, "Four"),
        (5, "Five"),
        (6, "Six")
    )

    search = forms.CharField(max_length=100)
    checkbox = forms.BooleanField(widget=forms.CheckboxInput)
    select = forms.TypedChoiceField(widget=forms.Select, choices=CHOICES)


class VerticalForm(InlineForm):

    failure_message = "Failed to complete operation"
    success_message = "Successfully completed the operation"

    CHOICES = (
        (1, "One"),
        (2, "Two"),
        (3, "Three"),
        (4, "Four"),
        (5, "Five"),
        (6, "Six")
    )

    name = forms.CharField(max_length=100)
    avatar = forms.ImageField()
    attachment = forms.FileField()
    # boolean_with_switch = forms.BooleanField(initial=False, help_text="Some useless advice", widget=SwitchInput)
    boolean_with_checkbox = forms.BooleanField(initial=False, help_text="Some useless advice")
    choices_with_radio = forms.TypedChoiceField(coerce=int, choices=CHOICES, widget=forms.RadioSelect)
    choices_with_select = forms.TypedChoiceField(coerce=int, choices=CHOICES, widget=forms.Select)
    multiple_choices_with_select = forms.TypedMultipleChoiceField(coerce=int, choices=CHOICES,
                                                             widget=forms.SelectMultiple)
    multiple_choices_with_checkbox = forms.TypedMultipleChoiceField(coerce=int, choices=CHOICES,
                                                      widget=forms.CheckboxSelectMultiple)
    age = forms.IntegerField()
    textarea = forms.CharField(widget=forms.Textarea, help_text="Text area is a good thing")
    date = forms.DateField()
    time = forms.TimeField()
    datetime = forms.DateTimeField()
