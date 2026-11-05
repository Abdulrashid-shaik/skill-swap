from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_matches


class DiscoverView(APIView):
    """GET /api/v1/discover/ — mutual matches for the authenticated user.
    Filters (narrow the 'they teach me' side): ?q= &category= &proficiency=.
    Delegates entirely to discovery.services.get_matches (no logic here)."""

    def get(self, request):
        matches = get_matches(
            request.user,
            q=request.query_params.get("q") or None,
            category=request.query_params.get("category") or None,
            proficiency=request.query_params.get("proficiency") or None,
        )
        results = []
        for m in matches:
            u = m["user"]
            results.append(
                {
                    "user": {
                        "id": u.pk,
                        "full_name": u.profile.full_name or "",
                        "username": u.username or "",
                        "rating_avg": str(u.profile.rating_avg),
                    },
                    "they_teach_me": [
                        {"skill": us.skill.name, "proficiency": us.proficiency}
                        for us in m["they_teach_me"]
                    ],
                    "i_teach_them": [s.name for s in m["i_teach_them"]],
                    "score": m["score"],
                }
            )
        return Response({"count": len(results), "results": results})
