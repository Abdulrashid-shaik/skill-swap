from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError
from apps.exchanges import services as ex_services
from apps.notifications.models import Notification, NotificationType
from apps.skills.models import (Skill, SkillCategory, SkillKind, SkillStatus,
                                UserSkill)

from . import services
from .models import ExchangeSession, SessionStatus


class SchedulingTests(TestCase):
    def setUp(self):
        cat = SkillCategory.objects.create(name="Programming")
        design = SkillCategory.objects.create(name="Design")
        self.python = Skill.objects.create(name="Python", category=cat, status=SkillStatus.APPROVED)
        self.uiux = Skill.objects.create(name="UI/UX", category=design, status=SkillStatus.APPROVED)
        self.alex = self._user("alex@x.com", [self.python], [self.uiux])
        self.sam = self._user("sam@x.com", [self.uiux], [self.python])
        self.rio = self._user("rio@x.com")
        req = ex_services.create_request(self.alex, self.sam, self.python, self.uiux)
        self.exchange = ex_services.accept_request(req, self.sam)
        self.start = timezone.now() + timedelta(days=1)
        self.end = self.start + timedelta(hours=1)

    def _user(self, email, offers=(), wants=()):
        u = User.objects.create_user(email=email, password="pw-strong-123")
        for s in offers:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.OFFER)
        for s in wants:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.WANT)
        return u

    def test_create_session_notifies_other(self):
        services.create_session(self.exchange, self.alex, title="Intro",
                                description="", start=self.start, end=self.end)
        self.assertEqual(self.exchange.sessions.count(), 1)
        self.assertTrue(Notification.objects.filter(
            recipient=self.sam, type=NotificationType.SESSION_SCHEDULED).exists())

    def test_non_participant_cannot_create(self):
        with self.assertRaises(BusinessRuleError):
            services.create_session(self.exchange, self.rio, title="x",
                                    description="", start=self.start, end=self.end)

    def test_reschedule_marks_old_and_creates_new(self):
        s = services.create_session(self.exchange, self.alex, title="Intro",
                                    description="", start=self.start, end=self.end)
        new_start = self.start + timedelta(days=1)
        new = services.reschedule_session(s, self.sam, start=new_start, end=new_start + timedelta(hours=1))
        s.refresh_from_db()
        self.assertEqual(s.status, SessionStatus.RESCHEDULED)
        self.assertEqual(new.status, SessionStatus.SCHEDULED)
        self.assertEqual(new.previous_session, s)

    def test_cancel_session(self):
        s = services.create_session(self.exchange, self.alex, title="Intro",
                                    description="", start=self.start, end=self.end)
        services.cancel_session(s, self.sam)
        s.refresh_from_db()
        self.assertEqual(s.status, SessionStatus.CANCELLED)

    def test_session_list_requires_participant(self):
        self.client.force_login(self.rio)
        self.assertEqual(
            self.client.get(reverse("session_list", args=[self.exchange.pk])).status_code, 404)

    def test_create_via_view(self):
        self.client.force_login(self.alex)
        resp = self.client.post(reverse("session_list", args=[self.exchange.pk]), {
            "title": "Session 1", "description": "Kickoff",
            "scheduled_start": "2027-01-01T10:00",
            "scheduled_end": "2027-01-01T11:00",
        })
        self.assertRedirects(resp, reverse("session_list", args=[self.exchange.pk]))
        self.assertTrue(ExchangeSession.objects.filter(title="Session 1").exists())

    def test_end_before_start_rejected(self):
        self.client.force_login(self.alex)
        resp = self.client.post(reverse("session_list", args=[self.exchange.pk]), {
            "title": "Bad", "description": "",
            "scheduled_start": "2027-01-01T11:00",
            "scheduled_end": "2027-01-01T10:00",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ExchangeSession.objects.filter(title="Bad").exists())
