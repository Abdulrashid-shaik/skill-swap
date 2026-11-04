from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from . import services


@login_required
def connect(request):
    if not services.is_enabled():
        messages.info(
            request,
            "Google Calendar integration is not configured in this environment yet.")
        return redirect("settings")
    try:
        return redirect(services.get_authorization_url(request))
    except services.IntegrationUnavailable as e:
        messages.error(request, str(e))
        return redirect("settings")


@login_required
def callback(request):
    try:
        services.handle_oauth_callback(request)
        messages.success(request, "Google Calendar connected.")
    except services.IntegrationUnavailable as e:
        messages.error(request, str(e))
    return redirect("settings")


@login_required
@require_POST
def disconnect(request):
    services.disconnect(request.user)
    messages.success(request, "Google Calendar disconnected.")
    return redirect("settings")
