from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.common.exceptions import BusinessRuleError

from . import services
from .models import UserBlock, UserReport


class ModerationServiceTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@x.com", password="pw-strong-123")
        self.b = User.objects.create_user(email="b@x.com", password="pw-strong-123")

    def test_block_and_unblock(self):
        services.block_user(self.a, self.b)
        self.assertTrue(UserBlock.objects.filter(blocker=self.a, blocked=self.b).exists())
        services.unblock_user(self.a, self.b)
        self.assertFalse(UserBlock.objects.filter(blocker=self.a, blocked=self.b).exists())

    def test_cannot_block_self(self):
        with self.assertRaises(BusinessRuleError):
            services.block_user(self.a, self.a)

    def test_block_is_idempotent(self):
        services.block_user(self.a, self.b)
        services.block_user(self.a, self.b)
        self.assertEqual(UserBlock.objects.filter(blocker=self.a, blocked=self.b).count(), 1)

    def test_report_creates_record(self):
        services.report_user(self.a, self.b, "spam", "spammy")
        self.assertTrue(UserReport.objects.filter(reporter=self.a, reported=self.b).exists())

    def test_cannot_report_self(self):
        with self.assertRaises(BusinessRuleError):
            services.report_user(self.a, self.a, "spam", "")


class ModerationViewTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@x.com", password="pw-strong-123")
        self.b = User.objects.create_user(email="b@x.com", password="pw-strong-123")
        self.client.force_login(self.a)

    def test_block_view(self):
        self.client.post(reverse("block_user", args=[self.b.pk]))
        self.assertTrue(UserBlock.objects.filter(blocker=self.a, blocked=self.b).exists())

    def test_report_view(self):
        resp = self.client.post(reverse("report_user", args=[self.b.pk]),
                                {"reason": "harassment", "description": "bad"})
        self.assertRedirects(resp, reverse("member_detail", args=[self.b.pk]))
        self.assertTrue(UserReport.objects.filter(reported=self.b).exists())
