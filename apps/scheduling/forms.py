from django import forms

from .models import ExchangeSession


class SessionForm(forms.ModelForm):
    class Meta:
        model = ExchangeSession
        fields = ["title", "description", "scheduled_start", "scheduled_end"]
        widgets = {
            "scheduled_start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "scheduled_end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("scheduled_start"), cleaned.get("scheduled_end")
        if start and end and end <= start:
            raise forms.ValidationError("The end time must be after the start time.")
        return cleaned
