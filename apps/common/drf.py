"""Shared DRF plumbing: exception handling, permissions, throttles.

The API is a thin layer over the existing service functions — business rules are
NOT re-implemented here. Services raise BusinessRuleError; the exception handler
below turns those into clean 400 responses so every endpoint surfaces rule
violations consistently.
"""
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import BusinessRuleError
from .ratelimit import LIMITS, by_user, check


def exception_handler(exc, context):
    """Map BusinessRuleError -> HTTP 400; defer everything else to DRF."""
    if isinstance(exc, BusinessRuleError):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return drf_exception_handler(exc, context)


class IsNotSuspended(BasePermission):
    """Defense-in-depth: refuse writes from suspended accounts. SuspensionMiddleware
    already blocks suspended users on /api/ with a 403, so this is a backstop
    that also documents intent at the view level."""

    message = "Your account is suspended."

    def has_permission(self, request, view):
        user = request.user
        return not (
            user.is_authenticated and getattr(user, "is_currently_suspended", False)
        )


class _DBScopedThrottle(BaseThrottle):
    """DRF throttle backed by the atomic DB limiter (apps.common.ratelimit),
    so API write limits share the same race-safe mechanism as the template
    views instead of DRF's non-atomic cache counters."""

    scope_name = "api"
    limit_key = None  # key into ratelimit.LIMITS

    def allow_request(self, request, view):
        rule = LIMITS[self.limit_key]
        allowed, retry_after = check(f"api:{self.scope_name}", by_user(request), rule)
        self._wait = retry_after
        return allowed

    def wait(self):
        return getattr(self, "_wait", None)


class MessageSendThrottle(_DBScopedThrottle):
    scope_name = "chat_send"
    limit_key = "chat_send"


class ReportThrottle(_DBScopedThrottle):
    scope_name = "report"
    limit_key = "report"


class RequestCreateThrottle(_DBScopedThrottle):
    scope_name = "request_create"
    limit_key = "request_create"
