from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(ListAPIView):
    """GET /api/v1/notifications/ — the user's own notifications."""

    serializer_class = NotificationSerializer

    def get_queryset(self):
        return self.request.user.notifications.all()


class NotificationMarkReadView(APIView):
    """POST /api/v1/notifications/<pk>/read/ — mark one as read (own only)."""

    def post(self, request, pk):
        note = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if not note.is_read:
            note.is_read = True
            note.read_at = timezone.now()
            note.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(note).data)


class NotificationMarkAllReadView(APIView):
    """POST /api/v1/notifications/read-all/ — mark all unread as read."""

    def post(self, request):
        updated = request.user.notifications.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"marked_read": updated})
