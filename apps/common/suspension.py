"""Central suspension guard for the service layer (defense-in-depth).

The middleware blocks suspended users at the HTTP boundary and DRF uses a
permission class, but service functions call this too so the rule holds even
if a caller reaches them another way. Checking the ``is_currently_suspended``
property means an expired suspension does not block (it reads as not suspended).
"""
from .exceptions import BusinessRuleError


def ensure_not_suspended(user, message="Your account is suspended."):
    """Raise BusinessRuleError if ``user`` is under an active suspension."""
    if getattr(user, "is_currently_suspended", False):
        raise BusinessRuleError(message)
