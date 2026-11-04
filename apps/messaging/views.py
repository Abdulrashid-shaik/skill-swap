import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.exchanges.models import Exchange
from apps.notifications.models import NotificationType
from apps.notifications.services import notify

from .models import Message


def _exchange_for(request, pk):
    exchange = get_object_or_404(Exchange, pk=pk)
    if not exchange.includes(request.user):
        raise Http404  # participants only — do not leak existence
    return exchange


def _serialize(m, me):
    return {
        "id": m.pk,
        "sender": m.sender.profile.full_name or m.sender.email,
        "body": m.body,
        "is_me": m.sender_id == me.pk,
        "created": timezone.localtime(m.created_at).strftime("%b %d, %H:%M"),
    }


def _mark_incoming_read(exchange, user):
    exchange.messages.exclude(sender=user).filter(is_read=False).update(
        is_read=True, read_at=timezone.now())


@login_required
@ensure_csrf_cookie
def chat(request, pk):
    exchange = _exchange_for(request, pk)
    _mark_incoming_read(exchange, request.user)
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
    data = [_serialize(m, request.user) for m in qs]
    _mark_incoming_read(exchange, request.user)
    return JsonResponse({"messages": data})


@login_required
@require_POST
def messages_send(request, pk):
    exchange = _exchange_for(request, pk)
    is_json = request.content_type == "application/json"
    if is_json:
        try:
            body = (json.loads(request.body).get("body") or "").strip()
        except (ValueError, AttributeError):
            body = ""
    else:
        body = (request.POST.get("body") or "").strip()

    if not body:
        if is_json:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)
        return redirect("exchange_chat", pk=exchange.pk)

    msg = Message.objects.create(exchange=exchange, sender=request.user, body=body)
    notify(
        exchange.other_participant(request.user),
        NotificationType.MESSAGE_RECEIVED,
        "New message in your exchange",
        target_url=f"/exchanges/{exchange.pk}/chat/",
    )
    if is_json:
        return JsonResponse({"message": _serialize(msg, request.user)}, status=201)
    return redirect("exchange_chat", pk=exchange.pk)
