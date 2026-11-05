from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.drf import IsNotSuspended, MessageSendThrottle
from apps.exchanges.models import Exchange

from . import services


def _exchange_or_404(request, pk):
    exchange = get_object_or_404(Exchange, pk=pk)
    if not exchange.includes(request.user):
        raise Http404  # participants only — do not leak existence
    return exchange


class MessageListView(APIView):
    """GET /api/v1/exchanges/<pk>/messages/?after=<id> — poll messages."""

    def get(self, request, pk):
        exchange = _exchange_or_404(request, pk)
        qs = exchange.messages.select_related("sender__profile")
        after = request.query_params.get("after")
        if after and after.isdigit():
            qs = qs.filter(pk__gt=int(after))
        data = [services.serialize_message(m, request.user) for m in qs]
        services.mark_incoming_read(exchange, request.user)
        return Response({"messages": data})


class MessageSendView(APIView):
    """POST /api/v1/exchanges/<pk>/messages/ — send a message."""

    permission_classes = APIView.permission_classes + [IsNotSuspended]
    throttle_classes = [MessageSendThrottle]

    def post(self, request, pk):
        exchange = _exchange_or_404(request, pk)
        # post_message raises BusinessRuleError (empty / suspended) -> 400 via
        # the shared exception handler.
        msg = services.post_message(exchange, request.user, request.data.get("body"))
        return Response(services.serialize_message(msg, request.user), status=201)
