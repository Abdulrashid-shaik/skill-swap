from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError
from apps.exchanges import services as ex_services
from apps.notifications.models import Notification, NotificationType
from apps.skills.models import (Skill, SkillCategory, SkillKind, SkillStatus,
                                UserSkill)

from . import services
from .models import Review


class ReviewTests(TestCase):
    def setUp(self):
        cat = SkillCategory.objects.create(name="Programming")
        design = SkillCategory.objects.create(name="Design")
        self.python = Skill.objects.create(name="Python", category=cat, status=SkillStatus.APPROVED)
        self.uiux = Skill.objects.create(name="UI/UX", category=design, status=SkillStatus.APPROVED)
        self.alex = self._user("alex@x.com", [self.python], [self.uiux])
        self.sam = self._user("sam@x.com", [self.uiux], [self.python])
        req = ex_services.create_request(self.alex, self.sam, self.python, self.uiux)
        self.exchange = ex_services.accept_request(req, self.sam)

    def _user(self, email, offers=(), wants=()):
        u = User.objects.create_user(email=email, password="pw-strong-123")
        for s in offers:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.OFFER)
        for s in wants:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.WANT)
        return u

    def _complete(self):
        ex_services.confirm_exchange(self.exchange.pk, self.alex)
        ex_services.confirm_exchange(self.exchange.pk, self.sam)
        self.exchange.refresh_from_db()

    def test_cannot_review_before_completion(self):
        with self.assertRaises(BusinessRuleError):
            services.create_review(self.exchange, self.alex, 5)

    def test_review_completed_updates_aggregate(self):
        self._complete()
        services.create_review(self.exchange, self.alex, 4, "Great")
        self.sam.profile.refresh_from_db()
        self.assertEqual(self.sam.profile.rating_count, 1)
        self.assertEqual(self.sam.profile.rating_avg, Decimal("4.00"))
        self.assertTrue(Notification.objects.filter(
            recipient=self.sam, type=NotificationType.REVIEW_RECEIVED).exists())

    def test_duplicate_review_rejected(self):
        self._complete()
        services.create_review(self.exchange, self.alex, 5)
        with self.assertRaises(BusinessRuleError):
            services.create_review(self.exchange, self.alex, 3)

    def test_non_participant_cannot_review(self):
        self._complete()
        rio = self._user("rio@x.com")
        with self.assertRaises(BusinessRuleError):
            services.create_review(self.exchange, rio, 5)

    def test_both_participants_review(self):
        self._complete()
        services.create_review(self.exchange, self.alex, 4)
        services.create_review(self.exchange, self.sam, 2)
        self.sam.profile.refresh_from_db()
        self.alex.profile.refresh_from_db()
        self.assertEqual(self.sam.profile.rating_avg, Decimal("4.00"))
        self.assertEqual(self.alex.profile.rating_avg, Decimal("2.00"))
        self.assertEqual(Review.objects.count(), 2)
