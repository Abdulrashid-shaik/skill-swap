from rest_framework.generics import RetrieveAPIView

from .models import UserProfile
from .serializers import ProfileSerializer


class MeView(RetrieveAPIView):
    """GET /api/v1/me/ — the authenticated user's own profile."""

    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile


class MemberProfileView(RetrieveAPIView):
    """GET /api/v1/members/<pk>/ — another member's public profile (pk = user id)."""

    serializer_class = ProfileSerializer
    queryset = UserProfile.objects.select_related("user")
    lookup_field = "user_id"
    lookup_url_kwarg = "pk"
