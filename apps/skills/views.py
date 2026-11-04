from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import SkillSuggestionForm, UserSkillForm
from .models import Skill, SkillCategory, SkillKind, SkillStatus, UserSkill


def _available_skills():
    return Skill.objects.filter(status=SkillStatus.APPROVED, is_active=True)


@login_required
def catalogue(request):
    """Browse/search the approved skill catalogue."""
    skills = _available_skills().select_related("category")
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    if query:
        skills = skills.filter(name__icontains=query)
    if category_slug:
        skills = skills.filter(category__slug=category_slug)
    return render(
        request,
        "skills/catalogue.html",
        {
            "skills": skills,
            "categories": SkillCategory.objects.all(),
            "query": query,
            "category_slug": category_slug,
        },
    )


@login_required
def my_skills(request):
    """Manage the user's teach (OFFER) and learn (WANT) lists."""
    if request.method == "POST":
        form = UserSkillForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            exists = UserSkill.objects.filter(
                user=request.user, skill=entry.skill, kind=entry.kind
            ).exists()
            if exists:
                form.add_error(None, "That skill is already in this list.")
            else:
                entry.save()
                return redirect("my_skills")
    else:
        form = UserSkillForm()

    user_skills = request.user.user_skills.select_related("skill", "skill__category")
    return render(
        request,
        "skills/my_skills.html",
        {
            "form": form,
            "offers": [s for s in user_skills if s.kind == SkillKind.OFFER],
            "wants": [s for s in user_skills if s.kind == SkillKind.WANT],
        },
    )


@login_required
@require_POST
def remove_user_skill(request, pk):
    """Remove one of the user's own skills (object-level ownership)."""
    entry = get_object_or_404(UserSkill, pk=pk, user=request.user)
    entry.delete()
    return redirect("my_skills")


@login_required
def suggest_skill(request):
    submitted = False
    if request.method == "POST":
        form = SkillSuggestionForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.status = SkillStatus.PENDING
            skill.suggested_by = request.user
            skill.save()
            form = SkillSuggestionForm()  # reset
            submitted = True
    else:
        form = SkillSuggestionForm()
    return render(
        request, "skills/suggest.html", {"form": form, "submitted": submitted}
    )
