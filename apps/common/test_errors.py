"""Branded error handling + notification open-redirect fix (Phase 7)."""
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.common import errors
from apps.notifications.models import Notification, NotificationType

PW = "pw-strong-123"


class ErrorHandlerUnitTests(TestCase):
    """Handlers are content-negotiated and never leak internals."""

    def setUp(self):
        self.rf = RequestFactory()

    def test_404_html(self):
        resp = errors.handler404(self.rf.get("/does-not-exist/"))
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b"couldn't find", resp.content)

    def test_404_json_for_api(self):
        resp = errors.handler404(self.rf.get("/api/v1/nope/"))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp["Content-Type"], "application/json")
        self.assertIn(b'"status": 404', resp.content)

    def test_403_html(self):
        resp = errors.handler403(self.rf.get("/secret/"))
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"permission", resp.content)

    def test_500_is_standalone_and_safe(self):
        # Rendered without a request context (no DB-touching context processors)
        # and never exposes internals.
        resp = errors.handler500(self.rf.get("/boom/"))
        self.assertEqual(resp.status_code, 500)
        self.assertIn(b"went wrong", resp.content)
        self.assertNotIn(b"Traceback", resp.content)

    def test_500_json_for_api(self):
        resp = errors.handler500(self.rf.get("/api/v1/boom/"))
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp["Content-Type"], "application/json")


class ErrorIntegrationTests(TestCase):
    def test_unknown_page_returns_branded_404(self):
        resp = self.client.get("/no-such-page/")
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, "couldn't find", status_code=404)

    def test_api_unknown_returns_json_404(self):
        resp = self.client.get("/api/v1/no-such-endpoint/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp["Content-Type"], "application/json")

    def test_wrong_method_returns_branded_405(self):
        # logout is POST-only; a GET yields 405, rebranded with an Allow header.
        resp = self.client.get(reverse("logout"))
        self.assertEqual(resp.status_code, 405)
        self.assertContains(resp, "isn't allowed", status_code=405)
        self.assertTrue(resp.has_header("Allow"))


class NotificationRedirectSafetyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="n@x.com", password=PW)
        self.client.force_login(self.user)

    def _note(self, target_url):
        return Notification.objects.create(
            recipient=self.user,
            type=NotificationType.MESSAGE_RECEIVED,
            title="t",
            target_url=target_url,
        )

    def test_external_target_url_is_not_followed(self):
        note = self._note("https://evil.example.com/phish")
        resp = self.client.post(reverse("notification_read", args=[note.pk]))
        # Falls back to the notifications list instead of the off-site URL.
        self.assertRedirects(resp, reverse("notification_list"))

    def test_safe_relative_target_url_is_followed(self):
        note = self._note("/requests/received/")
        resp = self.client.post(reverse("notification_read", args=[note.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/requests/received/")
