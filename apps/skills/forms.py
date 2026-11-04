from django import forms

from .models import Skill, SkillKind, SkillStatus, UserSkill


class UserSkillForm(forms.ModelForm):
    """Add a skill to the user's teach/learn list. Only approved, active
    skills may be chosen."""

    class Meta:
        model = UserSkill
        fields = ["skill", "kind", "proficiency", "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skill"].queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED, is_active=True
        )


class SkillSuggestionForm(forms.ModelForm):
    """Suggest a new skill for admin approval (R13)."""

    class Meta:
        model = Skill
        fields = ["name", "category", "description"]

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        category = cleaned.get("category")
        if name and category and Skill.objects.filter(
            name__iexact=name, category=category
        ).exists():
            raise forms.ValidationError(
                "A skill with this name already exists in that category."
            )
        return cleaned
