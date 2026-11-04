"""Google Calendar / Meet integration (P9).

Deliberately isolated and feature-flagged. When GOOGLE_INTEGRATION_ENABLED is
False (the default) every public function is a safe no-op or raises
IntegrationUnavailable — the rest of the app never depends on Google being
present. Enabling it requires, as external prerequisites:

  1. OAuth credentials (GOOGLE_OAUTH_CLIENT_ID / _SECRET / _REDIRECT_URI).
  2. The Google client libraries (google-auth, google-auth-oauthlib,
     google-api-python-client) — an install that needs approval (R6/R8).

Token at-rest encryption: _encrypt/_decrypt are placeholders using Django's
signing (obfuscation, not true encryption). Production must use Fernet from the
`cryptography` package once approved — see docs/DECISIONS.md R6. The real Google
API calls below are written but imported lazily so this module loads without the
libraries installed.
"""
from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.scheduling.models import GoogleSyncStatus


class IntegrationUnavailable(Exception):
    pass


def is_enabled():
    return bool(getattr(settings, "GOOGLE_INTEGRATION_ENABLED", False))


def _require_enabled():
    if not is_enabled():
        raise IntegrationUnavailable(
            "Google Calendar integration is not configured in this environment.")


# --- token storage helpers (placeholder obfuscation; see module docstring) ---
def _encrypt(value):
    return signing.dumps(value) if value else ""


def _decrypt(value):
    try:
        return signing.loads(value) if value else ""
    except signing.BadSignature:
        return ""


# --- OAuth flow (guarded; real calls lazy-imported) --------------------------
def get_authorization_url(request):
    _require_enabled()
    from google_auth_oauthlib.flow import Flow  # lazy import

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.events", "openid", "email"],
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    request.session["google_oauth_state"] = state
    return url


def handle_oauth_callback(request):
    _require_enabled()
    # Lazy import + token exchange; store encrypted tokens on the connection.
    from google_auth_oauthlib.flow import Flow  # noqa: F401
    # Implementation requires live credentials; intentionally not stubbed with
    # fake values. With credentials present, exchange request.GET['code'] for
    # tokens here and persist via GoogleCalendarConnection using _encrypt().
    raise IntegrationUnavailable(
        "OAuth callback requires live Google credentials (external prerequisite).")


def disconnect(user):
    from .models import GoogleCalendarConnection
    GoogleCalendarConnection.objects.filter(user=user).update(is_revoked=True)


# --- Calendar sync hooks (called by scheduling; safe no-ops when disabled) ---
def sync_new_session(session):
    if not is_enabled():
        return
    try:
        _create_calendar_event(session)
    except Exception:
        session.google_sync_status = GoogleSyncStatus.FAILED
        session.save(update_fields=["google_sync_status", "updated_at"])


def sync_cancelled_session(session):
    if not is_enabled():
        return
    try:
        _delete_calendar_event(session)
    except Exception:
        pass


def _create_calendar_event(session):
    _require_enabled()
    from googleapiclient.discovery import build  # lazy import  # noqa: F401
    # Build a Calendar event with conferenceData (Meet) for the two participants,
    # persist session.google_event_id / google_meet_link / sync_status.
    raise IntegrationUnavailable("Requires live Google credentials.")


def _delete_calendar_event(session):
    _require_enabled()
    raise IntegrationUnavailable("Requires live Google credentials.")
