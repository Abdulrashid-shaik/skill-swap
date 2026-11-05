"""Branded, content-negotiated error handling.

HTML visitors get on-brand pages (extending base.html, except 500 which is
standalone so it renders even if the database is down). API/AJAX clients get a
small JSON envelope. No internal exception details or stack traces are exposed
(DEBUG is False outside local debugging).

Wired via handler400/403/404/500 in config/urls.py, plus BrandedErrorMiddleware
for 405 (Method Not Allowed), which Django has no template hook for.
"""
import logging

from django.http import HttpResponse, JsonResponse
from django.template import loader

logger = logging.getLogger("skillswap")


def wants_json(request):
    """True when the caller expects JSON rather than an HTML page."""
    accept = request.META.get("HTTP_ACCEPT", "")
    return (
        request.path.startswith("/api/")
        or request.headers.get("x-requested-with") == "XMLHttpRequest"
        or ("application/json" in accept and "text/html" not in accept)
    )


def _error(request, status, template, message, *, use_request=True):
    if wants_json(request):
        return JsonResponse({"detail": message, "status": status}, status=status)
    # 500 renders without a request context so context processors (which touch
    # the DB) cannot re-raise while handling an error.
    context_request = request if use_request else None
    html = loader.render_to_string(template, {}, request=context_request)
    return HttpResponse(html, status=status)


def handler400(request, exception=None):
    return _error(request, 400, "400.html", "The request could not be processed.")


def handler403(request, exception=None):
    return _error(request, 403, "403.html", "You don't have permission to do that.")


def handler404(request, exception=None):
    return _error(request, 404, "404.html", "The requested resource was not found.")


def handler500(request):
    # Log at error level (also captured by the error log stream).
    logger.error("Unhandled server error on %s", request.path)
    return _error(
        request, 500, "500.html", "Something went wrong on our end.",
        use_request=False,
    )


class BrandedErrorMiddleware:
    """Rebrand bare 405 (Method Not Allowed) responses — Django returns a plain
    HttpResponseNotAllowed with no template hook. Preserves the Allow header.
    API/AJAX callers get JSON; HTML visitors get the branded 405 page. DRF
    handles its own 405s for /api/ routes (Phase 8), so we skip JSON paths."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 405 and not wants_json(request):
            allow = response.get("Allow", "")
            html = loader.render_to_string("405.html", {}, request=request)
            branded = HttpResponse(html, status=405)
            if allow:
                branded["Allow"] = allow
            return branded
        return response
