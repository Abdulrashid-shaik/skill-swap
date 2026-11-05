"""Fixed-window rate limiting, backed by an atomic DB counter.

Why not Django's cache framework? ``cache.incr()`` is a non-atomic
read-modify-write on the LocMem and DatabaseCache backends, so under concurrent
requests two callers can both read N and both write N+1 — undercounting and
letting requests slip past the limit. Instead we increment a dedicated DB row
with a single ``UPDATE ... F('count') + 1`` statement, which is atomic even on
SQLite (one write, serialized by the write lock). The limiter therefore fails
*closed*: a race over-counts at worst, never under-counts.

Usage:

    from apps.common.ratelimit import RateLimit, rate_limit, LIMITS

    @rate_limit("report", LIMITS["report"], ident=by_user)
    def report(request, pk): ...

Class-based auth views call :func:`check` directly (see accounts.views).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as _tz
from functools import wraps

from django.conf import settings
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone

from .models import RateLimitCounter


@dataclass(frozen=True)
class RateLimit:
    """A limit of ``limit`` requests per ``window`` seconds."""

    limit: int
    window: int


# Central registry of limits. Kept here so they are documented in one place and
# easy to tune. IP-based limits blunt spray/mass abuse; account-based limits
# blunt targeted abuse. Login is checked on BOTH axes.
LIMITS: dict[str, RateLimit] = {
    "login_ip": RateLimit(limit=30, window=300),      # 30 / 5 min per IP
    "login_email": RateLimit(limit=8, window=300),    # 8 / 5 min per account
    "register": RateLimit(limit=10, window=3600),     # 10 / hour per IP
    "password_reset_ip": RateLimit(limit=10, window=3600),     # 10 / hour per IP
    "password_reset_email": RateLimit(limit=5, window=3600),   # 5 / hour per account
    "chat_send": RateLimit(limit=30, window=60),      # 30 / min per account
    "report": RateLimit(limit=5, window=3600),        # 5 / hour per account
    "request_create": RateLimit(limit=30, window=3600),  # 30 / hour per account (API)
}


def _window_start(now: datetime, window: int) -> datetime:
    """Return the aligned start of the fixed window containing ``now``."""
    epoch = int(now.timestamp())
    bucket = epoch - (epoch % window)
    return datetime.fromtimestamp(bucket, tz=_tz.utc)


def check(scope: str, ident: str, rule: RateLimit, *, now: datetime | None = None):
    """Record one hit against ``(scope, ident)`` and report whether it is allowed.

    Returns ``(allowed: bool, retry_after: int)``. ``retry_after`` is seconds
    until the current window ends (>=1) when blocked, else 0.
    """
    now = now or timezone.now()
    start = _window_start(now, rule.window)

    # get_or_create is race-safe against the unique constraint (a losing racer
    # catches IntegrityError internally and re-selects the existing row).
    obj, _created = RateLimitCounter.objects.get_or_create(
        scope=scope, ident=ident[:190], window_start=start, defaults={"count": 0}
    )
    # Atomic increment — a single UPDATE statement.
    RateLimitCounter.objects.filter(pk=obj.pk).update(count=F("count") + 1)
    current = RateLimitCounter.objects.values_list("count", flat=True).get(pk=obj.pk)

    if current > rule.limit:
        retry_after = int(start.timestamp() + rule.window - now.timestamp())
        return False, max(retry_after, 1)
    return True, 0


def client_ip(request) -> str:
    """Best-effort client IP for IP-based limiting.

    ``X-Forwarded-For`` is client-spoofable, so by default we use the real
    peer address (``REMOTE_ADDR``). Only when ``RATELIMIT_TRUSTED_PROXY_COUNT``
    is set > 0 (meaning that many reverse proxies you control sit in front of
    the app and append to XFF) do we read the forwarded chain, taking the entry
    added by the outermost *trusted* proxy. Entries further left are supplied by
    the client and must not be trusted. Misconfiguring this to trust an
    untrusted header would let an attacker rotate the apparent IP to dodge
    limits — hence the conservative default of 0.
    """
    trusted = int(getattr(settings, "RATELIMIT_TRUSTED_PROXY_COUNT", 0) or 0)
    if trusted > 0:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            idx = max(len(parts) - trusted, 0)
            return parts[idx]
    return request.META.get("REMOTE_ADDR") or "unknown"


def by_user(request) -> str:
    """Identity function for account-based limits (authenticated views)."""
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return f"ip:{client_ip(request)}"


def _wants_json(request) -> bool:
    return (
        request.path.startswith("/api/")
        or request.content_type == "application/json"
        or request.headers.get("x-requested-with") == "XMLHttpRequest"
    )


def too_many(request, retry_after: int) -> HttpResponse:
    """Build a 429 response: JSON for API/AJAX requests, the branded page else."""
    if _wants_json(request):
        resp = JsonResponse(
            {
                "detail": "Request was throttled. Please try again later.",
                "code": "throttled",
                "retry_after": retry_after,
            },
            status=429,
        )
    else:
        html = render_to_string(
            "429.html", {"retry_after": retry_after}, request=request
        )
        resp = HttpResponse(html, status=429)
    resp["Retry-After"] = str(retry_after)
    return resp


def rate_limit(scope: str, rule: RateLimit, *, ident=client_ip, methods=("POST",)):
    """Decorator for function-based views. Limits only the given ``methods``
    (writes by default); reads pass through. ``ident`` maps a request to the
    limiting key (IP by default; pass ``by_user`` for account-based limits)."""

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method in methods:
                allowed, retry_after = check(scope, ident(request), rule)
                if not allowed:
                    return too_many(request, retry_after)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
