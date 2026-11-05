import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.common.exceptions import BusinessRuleError
from apps.common.ratelimit import LIMITS, by_user, rate_limit
from apps.exchanges.models import Exchange

from . import services


def _exchange_for(request, pk):
    exchange = get_object_or_404(Exchange, pk=pk)
    if not exchange.includes(request.user):
        raise Http404  # participants only — do not leak existence
    return exchange


@login_required
@ensure_csrf_cookie
def chat(request, pk):
    exchange = _exchange_for(request, pk)
    services.mark_incoming_read(exchange, request.user)
    msgs = list(exchange.messages.select_related("sender__profile"))
    return render(request, "messaging/chat.html", {
        "exchange": exchange,
        "chat_messages": msgs,
        "last_message_id": msgs[-1].pk if msgs else 0,
        "other": exchange.other_participant(request.user),
    })


@login_required
@require_GET
def messages_poll(request, pk):
    exchange = _exchange_for(request, pk)
    qs = exchange.messages.select_related("sender__profile")
    after = request.GET.get("after")
    if after and after.isdigit():
        qs = qs.filter(pk__gt=int(after))
    data = [services.serialize_message(m, request.user) for m in qs]
    services.mark_incoming_read(exchange, request.user)
    return JsonResponse({"messages": data})


@login_required
@require_POST
@rate_limit("chat_send", LIMITS["chat_send"], ident=by_user)
def messages_send(request, pk):
    exchange = _exchange_for(request, pk)
    is_json = request.content_type == "application/json"
    if is_json:
        try:
            body = json.loads(request.body).get("body")
        except (ValueError, AttributeError):
            body = ""
    else:
        body = request.POST.get("body")

    try:
        msg = services.post_message(exchange, request.user, body)
    except BusinessRuleError as e:
        if is_json:
            return JsonResponse({"error": str(e)}, status=400)
        return redirect("exchange_chat", pk=exchange.pk)

    if is_json:
        return JsonResponse(
            {"message": services.serialize_message(msg, request.user)}, status=201
        )
    return redirect("exchange_chat", pk=exchange.pk)
