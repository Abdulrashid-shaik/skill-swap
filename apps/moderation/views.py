from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError
from apps.common.ratelimit import LIMITS, by_user, rate_limit

from . import services
from .forms import ReportForm


@login_required
@require_POST
def block(request, pk):
    target = get_object_or_404(User, pk=pk)
    try:
        services.block_user(request.user, target)
        messages.success(request, "Member blocked.")
    except BusinessRuleError as e:
        messages.error(request, str(e))
    return redirect("member_detail", pk=pk)


@login_required
@require_POST
def unblock(request, pk):
    target = get_object_or_404(User, pk=pk)
    services.unblock_user(request.user, target)
    messages.success(request, "Member unblocked.")
    return redirect("member_detail", pk=pk)


@login_required
@rate_limit("report", LIMITS["report"], ident=by_user, methods=("POST",))
def report(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            try:
                services.report_user(
                    request.user, target,
                    form.cleaned_data["reason"], form.cleaned_data["description"])
                messages.success(request, "Report submitted. Thank you.")
                return redirect("member_detail", pk=pk)
            except BusinessRuleError as e:
                messages.error(request, str(e))
    else:
        form = ReportForm()
    return render(request, "moderation/report_form.html",
                  {"target": target, "form": form})
