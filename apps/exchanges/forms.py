from django import forms

from .models import ExchangeRequest


class ExchangeRequestForm(forms.ModelForm):
    class Meta:
        model = ExchangeRequest
        fields = ["offered_skill", "requested_skill", "message"]
        labels = {
            "offered_skill": "A skill you will teach them",
            "requested_skill": "A skill you want to learn from them",
        }

    def __init__(self, *args, offered_qs=None, requested_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if offered_qs is not None:
            self.fields["offered_skill"].queryset = offered_qs
        if requested_qs is not None:
            self.fields["requested_skill"].queryset = requested_qs
