"""Authentication backend that enforces account suspension at login time."""
import logging

from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger("skillswap.security")


class SuspensionAwareModelBackend(ModelBackend):
    """Email-login credential check (parent ModelBackend) plus a suspension gate
    on *login only*. An expired suspension is lifted lazily first, so the member
    regains access automatically (R12). Staff are exempt so administrative
    access is preserved. Deactivated / inactive accounts are already rejected by
    the parent (is_active=False).

    We override ``authenticate`` (login) rather than ``user_can_authenticate``,
    because the latter is also consulted by ``get_user`` on every request —
    blocking there would silently turn a suspended user's existing session into
    an anonymous one (a bare login redirect) instead of letting
    ``SuspensionMiddleware`` show a proper "account suspended" response.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(
            request, username=username, password=password, **kwargs
        )
        if user is None:
            return None
        user.lift_suspension_if_expired()
        if user.is_currently_suspended and not user.is_staff:
            logger.warning("Rejected login for suspended account id=%s", user.pk)
            return None
        return user
