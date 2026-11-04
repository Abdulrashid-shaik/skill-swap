"""Tests for ForwardedPrefixMiddleware (path-prefix / proxy handling)."""
from django.test import RequestFactory, TestCase, override_settings
from django.urls import get_script_prefix, set_script_prefix

from apps.common.middleware import ForwardedPrefixMiddleware


class ForwardedPrefixMiddlewareTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.captured = {}

        def get_response(request):
            # Snapshot what the resolver/reverse() would see at view time.
            self.captured["path_info"] = request.path_info
            self.captured["path"] = request.path
            self.captured["script_prefix"] = get_script_prefix()
            self.captured["script_name"] = request.META.get("SCRIPT_NAME", "")
            from django.http import HttpResponse

            return HttpResponse("ok")

        self.mw = ForwardedPrefixMiddleware(get_response)

    def tearDown(self):
        set_script_prefix("/")

    def test_absproxy_prefix_is_stripped_and_applied(self):
        """code-server /absproxy/<port>/ forwards the full path."""
        set_script_prefix("/")
        req = self.rf.get("/absproxy/8011/discover/")
        self.mw(req)
        # Resolver sees the clean path...
        self.assertEqual(self.captured["path_info"], "/discover/")
        # ...and reverse() re-adds the prefix.
        self.assertEqual(self.captured["script_prefix"], "/absproxy/8011/")
        self.assertEqual(self.captured["script_name"], "/absproxy/8011")

    def test_absproxy_root(self):
        set_script_prefix("/")
        req = self.rf.get("/absproxy/8011/")
        self.mw(req)
        self.assertEqual(self.captured["path_info"], "/")
        self.assertEqual(self.captured["script_prefix"], "/absproxy/8011/")

    @override_settings(APP_URL_PREFIX="/proxy/8899")
    def test_configured_prefix_on_clean_path(self):
        """A stripping proxy (code-server /proxy/<port>/) sends a clean path and
        no header; the configured prefix must still be added to generated URLs
        so links point back through the mount."""
        set_script_prefix("/")
        req = self.rf.get("/exchanges/")
        self.mw(req)
        # Path was already clean — leave it for the resolver...
        self.assertEqual(self.captured["path_info"], "/exchanges/")
        # ...but reverse() / {% url %} must re-add the configured prefix.
        self.assertEqual(self.captured["script_prefix"], "/proxy/8899/")
        self.assertEqual(self.captured["script_name"], "/proxy/8899")
        # request.path carries the prefix so ?next= login redirects stay in the
        # mount (get_full_path() reads request.path).
        self.assertEqual(self.captured["path"], "/proxy/8899/exchanges/")

    @override_settings(APP_URL_PREFIX="/proxy/8899")
    def test_configured_prefix_strips_when_path_carries_it(self):
        """If the proxy does forward the prefix in the path, strip it once."""
        set_script_prefix("/")
        req = self.rf.get("/proxy/8899/exchanges/")
        self.mw(req)
        self.assertEqual(self.captured["path_info"], "/exchanges/")
        self.assertEqual(self.captured["script_prefix"], "/proxy/8899/")

    @override_settings(APP_URL_PREFIX="/proxy/8899")
    def test_configured_prefix_takes_priority_over_autodetect(self):
        """An explicit prefix wins over a numeric-looking path segment."""
        set_script_prefix("/")
        req = self.rf.get("/absproxy/1234/exchanges/")
        self.mw(req)
        # Configured prefix is applied; the /absproxy/1234 segment is left as a
        # normal path (it is not the configured mount), so it does not resolve
        # here — the operator is responsible for a correct APP_URL_PREFIX.
        self.assertEqual(self.captured["script_prefix"], "/proxy/8899/")
        self.assertEqual(self.captured["path_info"], "/absproxy/1234/exchanges/")

    def test_x_forwarded_prefix_header_without_path_strip(self):
        """A reverse proxy that strips the prefix sends it in a header."""
        set_script_prefix("/")
        req = self.rf.get("/discover/", HTTP_X_FORWARDED_PREFIX="/myprefix")
        self.mw(req)
        # Path already clean (proxy stripped it) — do NOT strip again.
        self.assertEqual(self.captured["path_info"], "/discover/")
        self.assertEqual(self.captured["script_prefix"], "/myprefix/")

    def test_direct_access_unchanged(self):
        set_script_prefix("/")
        req = self.rf.get("/discover/")
        self.mw(req)
        self.assertEqual(self.captured["path_info"], "/discover/")
        self.assertEqual(self.captured["script_prefix"], "/")
        self.assertEqual(self.captured["script_name"], "")

    def test_non_proxy_numeric_path_not_treated_as_prefix(self):
        """A legitimate path must not be mistaken for a proxy prefix."""
        set_script_prefix("/")
        req = self.rf.get("/members/8011/")
        self.mw(req)
        self.assertEqual(self.captured["path_info"], "/members/8011/")
        self.assertEqual(self.captured["script_prefix"], "/")
