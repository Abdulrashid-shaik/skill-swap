from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.skills.models import Proficiency, SkillCategory

from .services import get_matches


@login_required
def discover(request):
    q = request.GET.get("q", "").strip() or None
    category = request.GET.get("category", "").strip() or None
    proficiency = request.GET.get("proficiency", "").strip() or None

    matches = get_matches(request.user, q=q, category=category, proficiency=proficiency)

    return render(
        request,
        "discovery/discover.html",
        {
            "matches": matches,
            "q": q or "",
            "category_slug": category or "",
            "proficiency": proficiency or "",
            "categories": SkillCategory.objects.all(),
            "proficiencies": Proficiency.choices,
        },
    )
