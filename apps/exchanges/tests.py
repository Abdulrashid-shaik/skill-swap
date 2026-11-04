from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError
from apps.moderation.models import UserBlock
from apps.skills.models import (Skill, SkillCategory, SkillKind, SkillStatus,
                                UserSkill)

from . import services
from .models import (Exchange, ExchangeConfirmation, ExchangeRequest,
                     ExchangeStatus, RequestStatus)


class ExchangeTestBase(TestCase):
    def setUp(self):
        self.cat = SkillCategory.objects.create(name="Programming")
        self.design = SkillCategory.objects.create(name="Design")
        self.python = Skill.objects.create(name="Python", category=self.cat, status=SkillStatus.APPROVED)
        self.uiux = Skill.objects.create(name="UI/UX", category=self.design, status=SkillStatus.APPROVED)
        self.sql = Skill.objects.create(name="SQL", category=self.cat, status=SkillStatus.APPROVED)
        # Alex <-> Sam are a valid mutual match.
        self.alex = self._user("alex@x.com", offers=[self.python], wants=[self.uiux])
        self.sam = self._user("sam@x.com", offers=[self.uiux], wants=[self.python])

    def _user(self, email, offers=(), wants=()):
        u = User.objects.create_user(email=email, password="pw-strong-123")
        for s in offers:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.OFFER)
        for s in wants:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.WANT)
        return u


class RequestRuleTests(ExchangeTestBase):
    def test_create_request_valid(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux, "hi")
        self.assertEqual(req.status, RequestStatus.PENDING)

    def test_cannot_request_non_match(self):
        rio = self._user("rio@x.com", offers=[self.sql], wants=[self.python])  # one-way
        with self.assertRaises(BusinessRuleError):
            services.create_request(self.alex, rio, self.python, self.sql)

    def test_no_duplicate_pending(self):
        services.create_request(self.alex, self.sam, self.python, self.uiux)
        with self.assertRaises(BusinessRuleError):
            services.create_request(self.alex, self.sam, self.python, self.uiux)

    def test_blocked_cannot_request(self):
        UserBlock.objects.create(blocker=self.sam, blocked=self.alex)
        with self.assertRaises(BusinessRuleError):
            services.create_request(self.alex, self.sam, self.python, self.uiux)

    def test_invalid_skill_pair_rejected(self):
        with self.assertRaises(BusinessRuleError):
            services.create_request(self.alex, self.sam, self.uiux, self.python)  # wrong direction


class AcceptRejectTests(ExchangeTestBase):
    def test_accept_creates_exchange(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux)
        exchange = services.accept_request(req, self.sam)
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.ACCEPTED)
        self.assertEqual(exchange.status, ExchangeStatus.ONGOING)
        self.assertEqual(exchange.participant_a, self.alex)
        self.assertEqual(exchange.skill_a_teaches, self.python)

    def test_only_receiver_can_accept(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux)
        with self.assertRaises(BusinessRuleError):
            services.accept_request(req, self.alex)  # sender cannot accept

    def test_only_sender_can_cancel(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux)
        with self.assertRaises(BusinessRuleError):
            services.cancel_request(req, self.sam)

    def test_accept_revalidates_match(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux)
        # Sam removes the wanted skill -> no longer a mutual match.
        UserSkill.objects.filter(user=self.sam, kind=SkillKind.WANT).delete()
        with self.assertRaises(BusinessRuleError):
            services.accept_request(req, self.sam)


class DualConfirmationTests(ExchangeTestBase):
    def _exchange(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux)
        return services.accept_request(req, self.sam)

    def test_first_confirmation_keeps_ongoing(self):
        ex = self._exchange()
        result = services.confirm_exchange(ex.pk, self.alex)
        ex.refresh_from_db()
        self.assertEqual(result, "awaiting_other")
        self.assertEqual(ex.status, ExchangeStatus.ONGOING)

    def test_second_confirmation_completes(self):
        ex = self._exchange()
        services.confirm_exchange(ex.pk, self.alex)
        result = services.confirm_exchange(ex.pk, self.sam)
        ex.refresh_from_db()
        self.assertEqual(result, "completed")
        self.assertEqual(ex.status, ExchangeStatus.COMPLETED)
        self.assertIsNotNone(ex.completed_at)
        self.alex.profile.refresh_from_db()
        self.sam.profile.refresh_from_db()
        self.assertEqual(self.alex.profile.completed_exchanges, 1)
        self.assertEqual(self.sam.profile.completed_exchanges, 1)

    def test_duplicate_confirmation_by_same_user_is_idempotent(self):
        ex = self._exchange()
        services.confirm_exchange(ex.pk, self.alex)
        services.confirm_exchange(ex.pk, self.alex)  # again — must not complete
        ex.refresh_from_db()
        self.assertEqual(ex.status, ExchangeStatus.ONGOING)
        self.assertEqual(ExchangeConfirmation.objects.filter(exchange=ex).count(), 1)

    def test_non_participant_cannot_confirm(self):
        ex = self._exchange()
        rio = self._user("rio@x.com")
        with self.assertRaises(BusinessRuleError):
            services.confirm_exchange(ex.pk, rio)

    def test_completed_exchange_cannot_be_reconfirmed(self):
        ex = self._exchange()
        services.confirm_exchange(ex.pk, self.alex)
        services.confirm_exchange(ex.pk, self.sam)
        with self.assertRaises(BusinessRuleError):
            services.confirm_exchange(ex.pk, self.alex)


class ExchangeViewTests(ExchangeTestBase):
    def test_detail_requires_participant(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux)
        ex = services.accept_request(req, self.sam)
        rio = self._user("rio@x.com")
        self.client.force_login(rio)
        self.assertEqual(self.client.get(reverse("exchange_detail", args=[ex.pk])).status_code, 404)

    def test_confirm_via_view(self):
        req = services.create_request(self.alex, self.sam, self.python, self.uiux)
        ex = services.accept_request(req, self.sam)
        self.client.force_login(self.alex)
        self.client.post(reverse("confirm_exchange", args=[ex.pk]))
        self.client.force_login(self.sam)
        self.client.post(reverse("confirm_exchange", args=[ex.pk]))
        ex.refresh_from_db()
        self.assertEqual(ex.status, ExchangeStatus.COMPLETED)
