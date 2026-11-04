from django.test import TestCase, override_settings

from apps.accounts.models import User

from . import services
from .models import GoogleCalendarConnection


class IntegrationDisabledTests(TestCase):
    """With the integration off (the default), the app must keep working and
    Google functions must be safe no-ops."""

    def test_is_disabled_by_default(self):
        self.assertFalse(services.is_enabled())

    def test_sync_new_session_is_noop_when_disabled(self):
        # Should not raise even with a dummy object.
        services.sync_new_session(object())

    @override_settings(GOOGLE_INTEGRATION_ENABLED=True)
    def test_authorization_requires_libraries(self):
        self.assertTrue(services.is_enabled())
        # Without the Google libraries installed, this raises ImportError —
        # which is expected in an environment where P9 is not provisioned.
        with self.assertRaises((ImportError, services.IntegrationUnavailable)):
            services.get_authorization_url(_DummyRequest())

    def test_token_obfuscation_roundtrip(self):
        token = "secret-token-value"
        self.assertEqual(services._decrypt(services._encrypt(token)), token)


class ConnectionModelTests(TestCase):
    def test_connection_model(self):
        u = User.objects.create_user(email="g@x.com", password="pw-strong-123")
        conn = GoogleCalendarConnection.objects.create(user=u, google_account_email="g@x.com")
        self.assertFalse(conn.is_revoked)
        services.disconnect(u)
        conn.refresh_from_db()
        self.assertTrue(conn.is_revoked)


class _DummyRequest:
    session = {}
