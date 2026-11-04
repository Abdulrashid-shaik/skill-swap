import json

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.exchanges import services as ex_services
from apps.notifications.models import Notification, NotificationType
from apps.skills.models import (Skill, SkillCategory, SkillKind, SkillStatus,
                                UserSkill)

from .models import Message


class MessagingTests(TestCase):
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

    def _user(self, email, offers=(), wants=()):
        u = User.objects.create_user(email=email, password="pw-strong-123")
        for s in offers:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.OFFER)
        for s in wants:
            UserSkill.objects.create(user=u, skill=s, kind=SkillKind.WANT)
        return u

    def _send(self, body):
        return self.client.post(
            reverse("messages_send", args=[self.exchange.pk]),
            data=json.dumps({"body": body}), content_type="application/json")

    def test_send_and_poll(self):
        self.client.force_login(self.alex)
        resp = self._send("Hello Sam")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Message.objects.filter(exchange=self.exchange, body="Hello Sam").exists())

        self.client.force_login(self.sam)
        poll = self.client.get(reverse("messages_poll", args=[self.exchange.pk]))
        data = poll.json()["messages"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["body"], "Hello Sam")
        # Sam viewing marks it read.
        self.assertTrue(Message.objects.get(body="Hello Sam").is_read)

    def test_send_creates_notification_for_other(self):
        self.client.force_login(self.alex)
        self._send("ping")
        self.assertTrue(Notification.objects.filter(
            recipient=self.sam, type=NotificationType.MESSAGE_RECEIVED).exists())

    def test_non_participant_cannot_access(self):
        self.client.force_login(self.rio)
        self.assertEqual(self.client.get(reverse("exchange_chat", args=[self.exchange.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("messages_poll", args=[self.exchange.pk])).status_code, 404)
        self.assertEqual(self._send("intrude").status_code, 404)

    def test_poll_after_returns_only_new(self):
        self.client.force_login(self.alex)
        self._send("first")
        self._send("second")
        first_id = Message.objects.get(body="first").pk
        poll = self.client.get(
            reverse("messages_poll", args=[self.exchange.pk]), {"after": first_id})
        bodies = [m["body"] for m in poll.json()["messages"]]
        self.assertEqual(bodies, ["second"])

    def test_empty_message_rejected(self):
        self.client.force_login(self.alex)
        self.assertEqual(self._send("   ").status_code, 400)
