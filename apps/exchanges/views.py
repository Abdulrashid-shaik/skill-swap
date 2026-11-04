from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError
from apps.discovery.services import are_mutually_compatible, exchangeable_skills
from apps.skills.models import Skill

from . import services
from .forms import ExchangeRequestForm
from .models import Exchange, ExchangeRequest


@login_required
def send_request(request, pk):
    receiver = get_object_or_404(User, pk=pk)
    compatible = are_mutually_compatible(request.user, receiver)
    a_teaches, b_teaches = exchangeable_skills(request.user, receiver)
    offered_qs = Skill.objects.filter(pk__in=[s.pk for s in a_teaches])
    requested_qs = Skill.objects.filter(pk__in=[s.pk for s in b_teaches])

    if request.method == "POST" and compatible:
        form = ExchangeRequestForm(
            request.POST, offered_qs=offered_qs, requested_qs=requested_qs)
        if form.is_valid():
            try:
                services.create_request(
                    request.user, receiver,
                    form.cleaned_data["offered_skill"],
                    form.cleaned_data["requested_skill"],
                    form.cleaned_data["message"],
                )
                messages.success(request, "Exchange request sent.")
                return redirect("requests_sent")
            except BusinessRuleError as e:
                messages.error(request, str(e))
    else:
        form = ExchangeRequestForm(offered_qs=offered_qs, requested_qs=requested_qs)

    return render(request, "exchanges/request_form.html", {
        "receiver": receiver, "form": form, "compatible": compatible,
        "a_teaches": a_teaches, "b_teaches": b_teaches,
    })


@login_required
def requests_sent(request):
    reqs = request.user.requests_sent.select_related(
        "receiver", "offered_skill", "requested_skill").order_by("-created_at")
    return render(request, "exchanges/requests_sent.html", {"requests": reqs})


@login_required
def requests_received(request):
    reqs = request.user.requests_received.select_related(
        "sender", "offered_skill", "requested_skill").order_by("-created_at")
    return render(request, "exchanges/requests_received.html", {"requests": reqs})


@login_required
@require_POST
def accept_request(request, pk):
    req = get_object_or_404(ExchangeRequest, pk=pk)
    try:
        exchange = services.accept_request(req, request.user)
        messages.success(request, "Request accepted — the exchange has started.")
        return redirect("exchange_detail", pk=exchange.pk)
    except BusinessRuleError as e:
        messages.error(request, str(e))
        return redirect("requests_received")


@login_required
@require_POST
def reject_request(request, pk):
    req = get_object_or_404(ExchangeRequest, pk=pk)
    try:
        services.reject_request(req, request.user)
        messages.success(request, "Request declined.")
    except BusinessRuleError as e:
        messages.error(request, str(e))
    return redirect("requests_received")


@login_required
@require_POST
def cancel_request(request, pk):
    req = get_object_or_404(ExchangeRequest, pk=pk)
    try:
        services.cancel_request(req, request.user)
        messages.success(request, "Request cancelled.")
    except BusinessRuleError as e:
        messages.error(request, str(e))
    return redirect("requests_sent")


def _get_member_exchange(request, pk):
    exchange = get_object_or_404(Exchange, pk=pk)
    if not exchange.includes(request.user):
        raise Http404
    return exchange


@login_required
def exchange_list(request):
    exchanges = Exchange.objects.filter(
        Q(participant_a=request.user) | Q(participant_b=request.user)
    ).select_related(
        "participant_a__profile", "participant_b__profile",
        "skill_a_teaches", "skill_b_teaches",
    ).order_by("-created_at")
    return render(request, "exchanges/exchange_list.html", {"exchanges": exchanges})


@login_required
def exchange_detail(request, pk):
    exchange = _get_member_exchange(request, pk)
    return render(request, "exchanges/exchange_detail.html", {
        "exchange": exchange,
        "other": exchange.other_participant(request.user),
        "has_confirmed": exchange.has_confirmed(request.user),
        "confirm_count": exchange.confirmations.count(),
    })


@login_required
@require_POST
def confirm_exchange(request, pk):
    exchange = _get_member_exchange(request, pk)
    try:
        result = services.confirm_exchange(exchange.pk, request.user)
        if result == "completed":
            messages.success(request, "Both of you confirmed — exchange completed!")
        else:
            messages.success(request, "Confirmation recorded. Waiting for your partner.")
    except BusinessRuleError as e:
        messages.error(request, str(e))
    return redirect("exchange_detail", pk=pk)


@login_required
@require_POST
def cancel_exchange(request, pk):
    exchange = _get_member_exchange(request, pk)
    try:
        services.cancel_exchange(exchange.pk, request.user)
        messages.success(request, "Exchange cancelled.")
    except BusinessRuleError as e:
        messages.error(request, str(e))
    return redirect("exchange_detail", pk=pk)
