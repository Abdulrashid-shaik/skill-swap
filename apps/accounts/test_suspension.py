"""Suspension enforcement across auth, existing sessions, services, discovery."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError
from apps.discovery.services import discoverable_users_qs
from apps.exchanges import services as exchange_services
from apps.skills.models import (Skill, SkillCategory, SkillKind, SkillStatus,
                                UserSkill)

PW = "pw-strong-123"


class SuspensionLoginTests(TestCase):
    """The auth backend refuses suspended accounts at login (new sessions)."""

    def test_indefinitely_suspended_cannot_log_in(self):
        u = User.objects.create_user(email="s@x.com", password=PW)
        u.is_suspended = True  # no suspended_until -> indefinite
        u.save()
        resp = self.client.post(
            reverse("login"), {"username": "s@x.com", "password": PW}
        )
        self.assertEqual(resp.status_code, 200)  # re-render, not a redirect
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_future_suspension_cannot_log_in(self):
        u = User.objects.create_user(email="s2@x.com", password=PW)
        u.is_suspended = True
        u.suspended_until = timezone.now() + timedelta(days=3)
        u.save()
        resp = self.client.post(
            reverse("login"), {"username": "s2@x.com", "password": PW}
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_expired_suspension_can_log_in_and_is_cleared(self):
        u = User.objects.create_user(email="s3@x.com", password=PW)
        u.is_suspended = True
        u.suspended_until = timezone.now() - timedelta(minutes=1)  # already expired
        u.save()
        resp = self.client.post(
            reverse("login"), {"username": "s3@x.com", "password": PW}
        )
        self.assertRedirects(resp, reverse("profile"))
        u.refresh_from_db()
        self.assertFalse(u.is_suspended)      # auto-expiry persisted (R12)
        self.assertIsNone(u.suspended_until)


class SuspensionSessionTests(TestCase):
    """Existing sessions must not let a suspended user keep using the app."""

    def setUp(self):
        self.user = User.objects.create_user(email="u@x.com", password=PW)

    def _suspend(self, until=None):
        self.user.is_suspended = True
        self.user.suspended_until = until
        self.user.save()

    def test_suspended_session_blocked_on_protected_page(self):
        self.client.force_login(self.user)
        self._suspend()
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, "suspended", status_code=403)

    def test_suspended_user_can_still_log_out(self):
        self.client.force_login(self.user)
        self._suspend()
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("home"))

    def test_expired_suspension_auto_clears_on_request(self):
        self.client.force_login(self.user)
        self._suspend(until=timezone.now() - timedelta(minutes=1))
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 200)  # expired -> allowed
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_suspended)

    def test_staff_are_exempt(self):
        # Preserve administrative access: a staff account is not locked out.
        staff = User.objects.create_user(email="mod@x.com", password=PW, is_staff=True)
        staff.is_suspended = True
        staff.save()
        self.client.force_login(staff)
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 200)


class SuspensionServiceGuardTests(TestCase):
    """Defense-in-depth: the service layer refuses suspended participants even
    if the HTTP middleware were bypassed (e.g. via the API)."""

    def setUp(self):
        cat = SkillCategory.objects.create(name="Programming")
        design = SkillCategory.objects.create(name="Design")
        self.python = Skill.objects.create(
            name="Python", category=cat, status=SkillStatus.APPROVED
        )
        self.uiux = Skill.objects.create(
            name="UI/UX", category=design, status=SkillStatus.APPROVED
        )
        self.alex = self._user("alex@x.com", offers=[self.python], wants=[self.uiux])
        self.sam = self._user("sam@x.com", offers=[self.uiux], wants=[self.python])

    def _user(self, email, offers=(), wants=()):
        u = User.objects.create_user(email=email, password=PW)
        for s in offers:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.OFFER)
        for s in wants:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.WANT)
        return u

    def test_suspended_sender_cannot_create_request(self):
        self.alex.is_suspended = True
        self.alex.save()
        with self.assertRaises(BusinessRuleError):
            exchange_services.create_request(
                self.alex, self.sam, self.python, self.uiux
            )

    def test_suspended_acceptor_cannot_accept(self):
        req = exchange_services.create_request(
            self.alex, self.sam, self.python, self.uiux
        )
        self.sam.is_suspended = True
        self.sam.save()
        with self.assertRaises(BusinessRuleError):
            exchange_services.accept_request(req, self.sam)

    def test_cannot_accept_when_sender_became_suspended(self):
        req = exchange_services.create_request(
            self.alex, self.sam, self.python, self.uiux
        )
        self.alex.is_suspended = True
        self.alex.save()
        with self.assertRaises(BusinessRuleError):
            exchange_services.accept_request(req, self.sam)


class SuspensionDiscoveryTests(TestCase):
    """Discovery honors auto-expiry (fixes the suspended_until gap)."""

    def setUp(self):
        self.me = User.objects.create_user(email="me@x.com", password=PW)

    def test_currently_suspended_user_is_hidden(self):
        other = User.objects.create_user(email="o@x.com", password=PW)
        other.is_suspended = True
        other.save()
        self.assertNotIn(other, discoverable_users_qs(self.me))

    def test_expired_suspension_user_is_visible_again(self):
        other = User.objects.create_user(email="o2@x.com", password=PW)
        other.is_suspended = True
        other.suspended_until = timezone.now() - timedelta(minutes=1)
        other.save()
        self.assertIn(other, discoverable_users_qs(self.me))
