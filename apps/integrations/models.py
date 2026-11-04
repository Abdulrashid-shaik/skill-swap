from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class GoogleCalendarConnection(TimeStampedModel):
    """Per-user Google OAuth connection (P9). Tokens are write-only — never
    serialized to any API response, template, or log. At-rest encryption is
    applied by the token helpers in services.py (see docs/DECISIONS.md R6)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="google_connection")
    google_account_email = models.EmailField(blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    scopes = models.TextField(blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)

    def __str__(self):
        return f"GoogleConnection<{self.user_id}>"
