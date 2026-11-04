from django import forms

from .models import UserReport


class ReportForm(forms.ModelForm):
    class Meta:
        model = UserReport
        fields = ["reason", "description"]
