from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.common.exceptions import BusinessRuleError
from apps.exchanges.models import Exchange

from . import services
from .forms import ReviewForm
from .models import Review


@login_required
def create_review(request, pk):
    exchange = get_object_or_404(Exchange, pk=pk)
    if not exchange.includes(request.user):
        raise Http404
    already = Review.objects.filter(exchange=exchange, reviewer=request.user).exists()
    if request.method == "POST" and not already:
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                services.create_review(
                    exchange, request.user,
                    form.cleaned_data["rating"], form.cleaned_data["feedback"])
                messages.success(request, "Thanks for your review.")
                return redirect("exchange_detail", pk=exchange.pk)
            except BusinessRuleError as e:
                messages.error(request, str(e))
    else:
        form = ReviewForm()
    return render(request, "reviews/review_form.html", {
        "exchange": exchange, "form": form, "already": already,
        "other": exchange.other_participant(request.user),
    })
