from rest_framework.generics import (ListAPIView, ListCreateAPIView,
                                     DestroyAPIView)

from apps.common.drf import IsNotSuspended

from .models import Skill, SkillStatus, UserSkill
from .serializers import SkillSerializer, UserSkillSerializer


class SkillCatalogueView(ListAPIView):
    """GET /api/v1/skills/ — the approved, active catalogue. Filters: ?q= &category=."""

    serializer_class = SkillSerializer

    def get_queryset(self):
        qs = Skill.objects.filter(
            status=SkillStatus.APPROVED, is_active=True
        ).select_related("category")
        q = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        if category:
            qs = qs.filter(category__slug=category)
        return qs


class MySkillsView(ListCreateAPIView):
    """GET/POST /api/v1/my-skills/ — the user's own OFFER/WANT entries."""

    serializer_class = UserSkillSerializer
    permission_classes = ListCreateAPIView.permission_classes + [IsNotSuspended]

    def get_queryset(self):
        return self.request.user.user_skills.select_related(
            "skill", "skill__category"
        )


class MySkillDeleteView(DestroyAPIView):
    """DELETE /api/v1/my-skills/<pk>/ — remove one of the user's own entries."""

    def get_queryset(self):
        # Object-level ownership: a user can only delete their own skills.
        return UserSkill.objects.filter(user=self.request.user)
