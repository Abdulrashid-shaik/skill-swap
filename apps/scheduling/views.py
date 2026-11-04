from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.common.exceptions import BusinessRuleError
from apps.exchanges.models import Exchange

from . import services
from .forms import SessionForm
from .models import ExchangeSession, SessionStatus


def _exchange_for(request, pk):
    exchange = get_object_or_404(Exchange, pk=pk)
    if not exchange.includes(request.user):
        raise Http404
    return exchange


def _session_for(request, pk):
    session = get_object_or_404(ExchangeSession, pk=pk)
    if not session.exchange.includes(request.user):
        raise Http404
    return session


@login_required
def session_list(request, pk):
    exchange = _exchange_for(request, pk)
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            services.create_session(
                exchange, request.user,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                start=form.cleaned_data["scheduled_start"],
                end=form.cleaned_data["scheduled_end"],
            )
            messages.success(request, "Session scheduled.")
            return redirect("session_list", pk=exchange.pk)
    else:
        form = SessionForm()

    now = timezone.now()
    sessions = exchange.sessions.all()
    upcoming = [s for s in sessions if s.scheduled_start >= now
                and s.status == SessionStatus.SCHEDULED]
    past = [s for s in sessions if s.scheduled_start < now
            or s.status != SessionStatus.SCHEDULED]
    return render(request, "scheduling/session_list.html", {
        "exchange": exchange, "form": form, "upcoming": upcoming, "past": past,
    })


@login_required
def reschedule_session(request, pk):
    session = _session_for(request, pk)
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            try:
                services.reschedule_session(
                    session, request.user,
                    start=form.cleaned_data["scheduled_start"],
                    end=form.cleaned_data["scheduled_end"],
                )
                messages.success(request, "Session rescheduled.")
                return redirect("session_list", pk=session.exchange.pk)
            except BusinessRuleError as e:
                messages.error(request, str(e))
    else:
        form = SessionForm(instance=session)
    return render(request, "scheduling/reschedule.html",
                  {"session": session, "form": form})


@login_required
@require_POST
def cancel_session(request, pk):
    session = _session_for(request, pk)
    try:
        services.cancel_session(session, request.user)
        messages.success(request, "Session cancelled.")
    except BusinessRuleError as e:
        messages.error(request, str(e))
    return redirect("session_list", pk=session.exchange.pk)


@login_required
@require_POST
def complete_session(request, pk):
    session = _session_for(request, pk)
    try:
        services.complete_session(session, request.user)
        messages.success(request, "Session marked complete.")
    except BusinessRuleError as e:
        messages.error(request, str(e))
    return redirect("session_list", pk=session.exchange.pk)
