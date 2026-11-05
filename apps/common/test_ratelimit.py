"""Tests for the atomic fixed-window rate limiter (apps/common/ratelimit)."""
import concurrent.futures
import threading
from datetime import timedelta

from django.db import connection
from django.test import (RequestFactory, TestCase, TransactionTestCase,
                         override_settings)
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.common.models import RateLimitCounter
from apps.common.ratelimit import RateLimit, check, client_ip


class FixedWindowLimiterTests(TestCase):
    def test_allows_up_to_limit_then_blocks(self):
        rule = RateLimit(limit=3, window=60)
        allowed = [check("t", "ip1", rule)[0] for _ in range(5)]
        self.assertEqual(allowed, [True, True, True, False, False])

    def test_each_call_increments_the_counter(self):
        rule = RateLimit(limit=100, window=60)
        for _ in range(4):
            check("t", "ip1", rule)
        row = RateLimitCounter.objects.get(scope="t", ident="ip1")
        self.assertEqual(row.count, 4)

    def test_separate_idents_have_independent_budgets(self):
        rule = RateLimit(limit=1, window=60)
        self.assertTrue(check("t", "a", rule)[0])
        self.assertTrue(check("t", "b", rule)[0])   # different ident
        self.assertFalse(check("t", "a", rule)[0])  # 'a' is exhausted

    def test_window_reset_allows_again(self):
        rule = RateLimit(limit=1, window=60)
        now = timezone.now()
        self.assertTrue(check("t", "ip", rule, now=now)[0])
        self.assertFalse(check("t", "ip", rule, now=now)[0])
        # The next fixed window is a fresh bucket.
        later = now + timedelta(seconds=61)
        self.assertTrue(check("t", "ip", rule, now=later)[0])

    def test_retry_after_is_bounded_and_positive_when_blocked(self):
        rule = RateLimit(limit=1, window=120)
        check("t", "ip", rule)
        allowed, retry = check("t", "ip", rule)
        self.assertFalse(allowed)
        self.assertGreater(retry, 0)
        self.assertLessEqual(retry, 120)


class ClientIpTrustedProxyTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_forwarded_for_ignored_by_default(self):
        # Default (no trusted proxies): the spoofable header is ignored.
        req = self.rf.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(client_ip(req), "10.0.0.1")

    @override_settings(RATELIMIT_TRUSTED_PROXY_COUNT=1)
    def test_trusted_proxy_entry_is_used(self):
        # With one trusted proxy, the right-most XFF entry (added by our proxy)
        # is the real client; left entries are attacker-supplied.
        req = self.rf.get(
            "/", HTTP_X_FORWARDED_FOR="9.9.9.9, 5.6.7.8", REMOTE_ADDR="10.0.0.1"
        )
        self.assertEqual(client_ip(req), "5.6.7.8")

    @override_settings(RATELIMIT_TRUSTED_PROXY_COUNT=1)
    def test_attacker_cannot_spoof_earlier_entries(self):
        req = self.rf.get(
            "/", HTTP_X_FORWARDED_FOR="evil-spoof, real-client", REMOTE_ADDR="10.0.0.1"
        )
        self.assertEqual(client_ip(req), "real-client")


class RegisterRateLimitViewTests(TestCase):
    def test_register_returns_429_after_limit(self):
        # LIMITS["register"] = 10/hour per IP. The 11th POST is throttled.
        last = None
        for i in range(10):
            last = self.client.post(
                reverse("register"),
                {"email": f"u{i}@example.com", "password1": "pw-strong-123",
                 "password2": "pw-strong-123"},
            )
            self.assertNotEqual(last.status_code, 429)
        blocked = self.client.post(
            reverse("register"),
            {"email": "u10@example.com", "password1": "pw-strong-123",
             "password2": "pw-strong-123"},
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)
        # Throttling happens before the view body, so no 11th user is created.
        self.assertFalse(User.objects.filter(email="u10@example.com").exists())


class LoginRateLimitViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="l@example.com", password="pw-strong-123"
        )

    def test_login_throttled_after_repeated_failures(self):
        # LIMITS["login_email"] = 8 / 5 min. The 9th attempt is throttled,
        # blunting brute-force against a single account.
        for _ in range(8):
            resp = self.client.post(
                reverse("login"),
                {"username": "l@example.com", "password": "wrong-password"},
            )
            self.assertEqual(resp.status_code, 200)  # re-render, not throttled
        blocked = self.client.post(
            reverse("login"),
            {"username": "l@example.com", "password": "wrong-password"},
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)


class LimiterConcurrencyTests(TransactionTestCase):
    """Separate DB connections (threads) hitting the same bucket. Verifies the
    F()-based increment is atomic and the limit cannot be exceeded under a race.
    Runs against the configured SQLite engine (WAL + busy_timeout)."""

    def _run(self, fn, n, workers=8):
        def worker(_):
            try:
                return fn()
            finally:
                connection.close()  # don't leak this thread's connection

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(worker, range(n)))

    def test_no_lost_updates_under_concurrency(self):
        rule = RateLimit(limit=10_000, window=300)  # high: nothing blocked
        n = 40
        self._run(lambda: check("conc", "ip", rule), n)
        row = RateLimitCounter.objects.get(scope="conc", ident="ip")
        self.assertEqual(row.count, n)  # atomic increments: no lost updates

    def test_limit_never_exceeded_under_concurrency(self):
        rule = RateLimit(limit=10, window=300)
        n = 40
        results = self._run(lambda: check("conc2", "ip", rule)[0], n)
        granted = sum(1 for ok in results if ok)
        # Fail-closed: never grant MORE than the limit (may grant fewer under a
        # read-back race, which is the safe direction).
        self.assertLessEqual(granted, 10)
        self.assertGreater(granted, 0)
        self.assertEqual(
            RateLimitCounter.objects.get(scope="conc2", ident="ip").count, n
        )
