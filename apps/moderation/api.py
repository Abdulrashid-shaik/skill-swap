from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.common.drf import IsNotSuspended, ReportThrottle

from . import services
from .serializers import ReportCreateSerializer


class ReportCreateView(APIView):
    """POST /api/v1/members/<pk>/report/ — report a member. Report *handling*
    stays in the Django admin; ordinary users can only file reports."""

    permission_classes = APIView.permission_classes + [IsNotSuspended]
    throttle_classes = [ReportThrottle]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        data = ReportCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.report_user(
            request.user, target,
            data.validated_data["reason"], data.validated_data["description"],
        )
        return Response({"detail": "Report submitted."}, status=201)
