from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import User, UserProfile


class RegistrationForm(forms.ModelForm):
    """Email + password registration. Username is an optional display handle."""

    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput, strip=False
    )
    password2 = forms.CharField(
        label="Confirm password", widget=forms.PasswordInput, strip=False
    )

    class Meta:
        model = User
        fields = ["email", "username"]

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two password fields didn't match.")
        validate_password(p2, self.instance)
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Edit own profile only (M2)."""

    class Meta:
        model = UserProfile
        fields = ["full_name", "avatar", "bio", "location", "experience_level"]
