"""Per-user concurrent-exchange rule (Phase 4).

A user may be in at most ONE ongoing exchange at a time, enforced for both
participants and safe under concurrent accepts. The real guarantee on SQLite is
the OngoingExchangeParticipant unique(user) constraint (select_for_update is a
no-op there), so the concurrency test runs against the configured file-based
SQLite engine with WAL + busy_timeout.
"""
import concurrent.futures
import threading

from django.db import connection
from django.test import TestCase, TransactionTestCase

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError
from apps.skills.models import (Skill, SkillCategory, SkillKind, SkillStatus,
                                UserSkill)

from . import services
from .models import (Exchange, ExchangeStatus, OngoingExchangeParticipant,
                     ExchangeRequest)

PW = "pw-strong-123"


class _Fixture:
    """Builds skills and typed users. '_px' teaches Python/wants UI; '_pu'
    teaches UI/wants Python — so every _px is a mutual match with every _pu."""

    def _build_skills(self):
        self.cat = SkillCategory.objects.create(name="Programming")
        self.design = SkillCategory.objects.create(name="Design")
        self.python = Skill.objects.create(
            name="Python", category=self.cat, status=SkillStatus.APPROVED
        )
        self.uiux = Skill.objects.create(
            name="UIUX", category=self.design, status=SkillStatus.APPROVED
        )

    def _user(self, email, offers=(), wants=()):
        u = User.objects.create_user(email=email, password=PW)
        for s in offers:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.OFFER)
        for s in wants:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.WANT)
        return u

    def _px(self, email):  # teaches Python, wants UI
        return self._user(email, offers=[self.python], wants=[self.uiux])

    def _pu(self, email):  # teaches UI, wants Python
        return self._user(email, offers=[self.uiux], wants=[self.python])


class ConcurrentExchangeRuleTests(_Fixture, TestCase):
    def setUp(self):
        self._build_skills()

    def test_user_with_no_ongoing_can_start_one(self):
        x, y = self._px("x@x.com"), self._pu("y@x.com")
        req = services.create_request(y, x, self.uiux, self.python)
        ex = services.accept_request(req, x)
        self.assertEqual(ex.status, ExchangeStatus.ONGOING)
        # Both participants hold a slot.
        self.assertEqual(
            OngoingExchangeParticipant.objects.filter(exchange=ex).count(), 2
        )

    def test_user_with_ongoing_cannot_start_another(self):
        x, y, z = self._px("x@x.com"), self._pu("y@x.com"), self._pu("z@x.com")
        services.accept_request(services.create_request(y, x, self.uiux, self.python), x)
        req2 = services.create_request(z, x, self.uiux, self.python)
        with self.assertRaises(BusinessRuleError):
            services.accept_request(req2, x)  # x is already ongoing
        # No second exchange was created (atomic rollback).
        self.assertEqual(Exchange.objects.filter(participant_b=x).count(), 1)

    def test_other_participant_is_also_protected(self):
        # The rule protects the SENDER too, not just the acceptor.
        x, y = self._px("x@x.com"), self._pu("y@x.com")
        services.accept_request(services.create_request(y, x, self.uiux, self.python), x)
        # y is now ongoing. y sends to w; w (free) tries to accept -> blocked.
        w = self._px("w@x.com")
        reqy2 = services.create_request(y, w, self.uiux, self.python)
        with self.assertRaises(BusinessRuleError):
            services.accept_request(reqy2, w)

    def test_completing_releases_the_slot(self):
        x, y, z = self._px("x@x.com"), self._pu("y@x.com"), self._pu("z@x.com")
        ex1 = services.accept_request(
            services.create_request(y, x, self.uiux, self.python), x
        )
        services.confirm_exchange(ex1.pk, x)
        services.confirm_exchange(ex1.pk, y)  # dual-confirm -> COMPLETED
        self.assertFalse(OngoingExchangeParticipant.objects.filter(user=x).exists())
        # x is free again.
        ex2 = services.accept_request(
            services.create_request(z, x, self.uiux, self.python), x
        )
        self.assertEqual(ex2.status, ExchangeStatus.ONGOING)

    def test_cancelling_releases_the_slot(self):
        x, y, z = self._px("x@x.com"), self._pu("y@x.com"), self._pu("z@x.com")
        ex1 = services.accept_request(
            services.create_request(y, x, self.uiux, self.python), x
        )
        services.cancel_exchange(ex1.pk, x)
        self.assertFalse(OngoingExchangeParticipant.objects.filter(user=x).exists())
        ex2 = services.accept_request(
            services.create_request(z, x, self.uiux, self.python), x
        )
        self.assertEqual(ex2.status, ExchangeStatus.ONGOING)

    def test_duplicate_pending_request_race_is_clean(self):
        # Bug B: a duplicate pending request surfaces a BusinessRuleError, never
        # an unhandled IntegrityError/500.
        x, y = self._px("x@x.com"), self._pu("y@x.com")
        services.create_request(y, x, self.uiux, self.python)
        with self.assertRaises(BusinessRuleError):
            services.create_request(y, x, self.uiux, self.python)


class ConcurrentAcceptBypassTests(_Fixture, TransactionTestCase):
    """Two simultaneous accepts that would both place X into an ongoing exchange
    must not both succeed — across separate DB connections."""

    def setUp(self):
        self._build_skills()
        self.x = self._px("x@x.com")
        y, z = self._pu("y@x.com"), self._pu("z@x.com")
        self.req1 = services.create_request(y, self.x, self.uiux, self.python)
        self.req2 = services.create_request(z, self.x, self.uiux, self.python)

    def test_concurrent_accepts_cannot_bypass_the_rule(self):
        outcomes = []
        lock = threading.Lock()

        def worker(req_id):
            try:
                req = ExchangeRequest.objects.get(pk=req_id)
                services.accept_request(req, self.x)
                result = "ok"
            except BusinessRuleError:
                result = "blocked"
            except Exception as exc:  # surface unexpected errors in the assert
                result = f"error:{exc!r}"
            finally:
                connection.close()
            with lock:
                outcomes.append(result)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            list(ex.map(worker, [self.req1.pk, self.req2.pk]))

        self.assertEqual(outcomes.count("ok"), 1, outcomes)       # exactly one won
        self.assertEqual(outcomes.count("blocked"), 1, outcomes)  # the other lost
        # X ends up in exactly one ongoing exchange, with exactly one lock row.
        self.assertEqual(OngoingExchangeParticipant.objects.filter(user=self.x).count(), 1)
        self.assertEqual(
            Exchange.objects.filter(
                participant_b=self.x, status=ExchangeStatus.ONGOING
            ).count(),
            1,
        )
