"""Suspension enforcement for already-authenticated sessions.

Login-time blocking lives in the auth backend; this middleware covers the case
where a user is suspended *after* logging in — their existing session must not
let them keep using protected functionality. It runs for every request
(templates and the API), so it is the central server-side gate; views/services
add defense-in-depth guards on top.
"""
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

logger = logging.getLogger("skillswap.security")


class SuspensionMiddleware:
    """Block currently-suspended, non-staff users from everything except
    logging out. Staff are exempt so moderators keep access to the admin and
    suspension management (requirement: preserve administrative access).
    Expired suspensions are lifted lazily here too."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_staff:
            user.lift_suspension_if_expired()
            if user.is_currently_suspended and not self._is_exempt(request):
                logger.warning(
                    "Blocked suspended account id=%s path=%s", user.pk, request.path
                )
                if request.path.startswith("/api/"):
                    return JsonResponse(
                        {
                            "detail": "Your account is suspended.",
                            "code": "account_suspended",
                        },
                        status=403,
                    )
                return render(
                    request,
                    "accounts/suspended.html",
                    {"suspended_until": user.suspended_until},
                    status=403,
                )
        return self.get_response(request)

    def _is_exempt(self, request):
        """Suspended users may still log out (and nothing else). Compare against
        the reversed URL so this stays correct under a path-prefix proxy."""
        try:
            logout_path = reverse("logout")
        except Exception:  # pragma: no cover - URLconf always has logout
            logout_path = "/logout/"
        return request.path == logout_path
