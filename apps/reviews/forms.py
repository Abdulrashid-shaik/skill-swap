from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, str(i)) for i in range(1, 6)], coerce=int,
        label="Rating (1–5)")

    class Meta:
        model = Review
        fields = ["rating", "feedback"]
