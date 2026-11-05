"""DRF endpoints for exchange requests and the exchange lifecycle.

Every state change delegates to apps.exchanges.services (the same code the
template views use), so the dual-confirmation, mutual-match, suspension and
per-user concurrency rules are enforced in exactly one place.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.common.drf import IsNotSuspended, RequestCreateThrottle
from apps.skills.models import Skill

from . import services
from .models import Exchange, ExchangeRequest
from .serializers import (ExchangeRequestCreateSerializer,
                          ExchangeRequestSerializer, ExchangeSerializer)


class RequestListView(ListAPIView):
    """GET /api/v1/requests/?box=received|sent"""

    serializer_class = ExchangeRequestSerializer

    def get_queryset(self):
        box = self.request.query_params.get("box", "received")
        user = self.request.user
        base = ExchangeRequest.objects.select_related(
            "sender__profile", "receiver__profile", "offered_skill", "requested_skill"
        )
        if box == "sent":
            return base.filter(sender=user).order_by("-created_at")
        return base.filter(receiver=user).order_by("-created_at")


class RequestCreateView(APIView):
    """POST /api/v1/requests/ — send an exchange request."""

    permission_classes = APIView.permission_classes + [IsNotSuspended]
    throttle_classes = [RequestCreateThrottle]

    def post(self, request):
        data = ExchangeRequestCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        receiver = get_object_or_404(User, pk=v["receiver_id"])
        offered = get_object_or_404(Skill, pk=v["offered_skill_id"])
        requested = get_object_or_404(Skill, pk=v["requested_skill_id"])
        req = services.create_request(
            request.user, receiver, offered, requested, v["message"]
        )
        return Response(
            ExchangeRequestSerializer(req).data, status=201
        )


class RequestActionView(APIView):
    """POST /api/v1/requests/<pk>/<action>/ where action is accept|reject|cancel."""

    permission_classes = APIView.permission_classes + [IsNotSuspended]
    ACTIONS = {
        "accept": services.accept_request,
        "reject": services.reject_request,
        "cancel": services.cancel_request,
    }

    def post(self, request, pk, action):
        if action not in self.ACTIONS:
            return Response({"detail": "Unknown action."}, status=400)
        # Scope to requests the user is a party to; others 404 (no info leak).
        req = get_object_or_404(
            ExchangeRequest.objects.filter(Q(sender=request.user) | Q(receiver=request.user)),
            pk=pk,
        )
        result = self.ACTIONS[action](req, request.user)
        if action == "accept":
            return Response(
                ExchangeSerializer(result, context={"request": request}).data,
                status=200,
            )
        req.refresh_from_db()
        return Response(ExchangeRequestSerializer(req).data, status=200)


class _ParticipantExchangeMixin:
    def get_queryset(self):
        user = self.request.user
        return Exchange.objects.filter(
            Q(participant_a=user) | Q(participant_b=user)
        ).select_related("participant_a__profile", "participant_b__profile")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class ExchangeListView(_ParticipantExchangeMixin, ListAPIView):
    """GET /api/v1/exchanges/ — the user's exchanges."""

    serializer_class = ExchangeSerializer

    def get_queryset(self):
        return super().get_queryset().order_by("-started_at")


class ExchangeDetailView(_ParticipantExchangeMixin, RetrieveAPIView):
    """GET /api/v1/exchanges/<pk>/ — participants only (others 404)."""

    serializer_class = ExchangeSerializer


class ExchangeConfirmView(APIView):
    """POST /api/v1/exchanges/<pk>/confirm/ — record this participant's completion
    confirmation (dual-confirmation enforced in the service)."""

    permission_classes = APIView.permission_classes + [IsNotSuspended]

    def post(self, request, pk):
        result = services.confirm_exchange(pk, request.user)
        return Response({"result": result})


class ExchangeCancelView(APIView):
    """POST /api/v1/exchanges/<pk>/cancel/ — cancel an ongoing exchange."""

    permission_classes = APIView.permission_classes + [IsNotSuspended]

    def post(self, request, pk):
        services.cancel_exchange(pk, request.user)
        return Response({"result": "cancelled"})
