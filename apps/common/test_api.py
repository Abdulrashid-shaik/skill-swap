"""Tests for the DRF API (/api/v1/) — auth, permissions, validation, flows."""
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.exchanges import services as exchange_services
from apps.exchanges.models import ExchangeStatus
from apps.skills.models import (Skill, SkillCategory, SkillKind, SkillStatus,
                                UserSkill)

PW = "pw-strong-123"


class ApiBase(TestCase):
    def setUp(self):
        self.cat = SkillCategory.objects.create(name="Programming")
        self.design = SkillCategory.objects.create(name="Design")
        self.python = Skill.objects.create(
            name="Python", category=self.cat, status=SkillStatus.APPROVED
        )
        self.uiux = Skill.objects.create(
            name="UIUX", category=self.design, status=SkillStatus.APPROVED
        )
        self.pending = Skill.objects.create(
            name="Rust", category=self.cat, status=SkillStatus.PENDING
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


class ApiAuthTests(ApiBase):
    def test_endpoints_require_authentication(self):
        for name in ["api:me", "api:skills", "api:discover", "api:notifications"]:
            resp = self.client.get(reverse(name))
            self.assertIn(resp.status_code, (401, 403), f"{name} -> {resp.status_code}")

    def test_me_returns_own_profile(self):
        self.client.force_login(self.alex)
        resp = self.client.get(reverse("api:me"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], "alex@x.com")


class ApiSkillTests(ApiBase):
    def test_catalogue_lists_only_approved(self):
        self.client.force_login(self.alex)
        resp = self.client.get(reverse("api:skills"))
        names = {s["name"] for s in resp.json()["results"]}
        self.assertIn("Python", names)
        self.assertNotIn("Rust", names)  # PENDING is hidden

    def test_add_my_skill_rejects_unapproved_skill(self):
        self.client.force_login(self.alex)
        resp = self.client.post(
            reverse("api:my_skills"),
            {"skill_id": self.pending.pk, "kind": SkillKind.OFFER},
        )
        self.assertEqual(resp.status_code, 400)

    def test_add_and_delete_my_skill(self):
        sql = Skill.objects.create(
            name="SQL", category=self.cat, status=SkillStatus.APPROVED
        )
        self.client.force_login(self.alex)
        resp = self.client.post(
            reverse("api:my_skills"),
            {"skill_id": sql.pk, "kind": SkillKind.OFFER},
        )
        self.assertEqual(resp.status_code, 201)
        skill_id = resp.json()["id"]
        # Another user cannot delete it (object-level ownership).
        self.client.force_login(self.sam)
        resp2 = self.client.delete(reverse("api:my_skill_delete", args=[skill_id]))
        self.assertEqual(resp2.status_code, 404)


class ApiDiscoverTests(ApiBase):
    def test_discover_returns_mutual_match(self):
        self.client.force_login(self.alex)
        resp = self.client.get(reverse("api:discover"))
        self.assertEqual(resp.status_code, 200)
        ids = {r["user"]["id"] for r in resp.json()["results"]}
        self.assertIn(self.sam.pk, ids)


class ApiExchangeFlowTests(ApiBase):
    def test_full_request_accept_confirm_flow(self):
        # Send a request (alex -> sam) via the API.
        self.client.force_login(self.alex)
        resp = self.client.post(
            reverse("api:request_create"),
            {"receiver_id": self.sam.pk, "offered_skill_id": self.python.pk,
             "requested_skill_id": self.uiux.pk, "message": "hi"},
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        req_id = resp.json()["id"]

        # Sam accepts.
        self.client.force_login(self.sam)
        resp = self.client.post(reverse("api:request_action", args=[req_id, "accept"]))
        self.assertEqual(resp.status_code, 200, resp.content)
        ex_id = resp.json()["id"]

        # Dual confirmation via the API.
        self.client.post(reverse("api:exchange_confirm", args=[ex_id]))  # sam
        self.client.force_login(self.alex)
        resp = self.client.post(reverse("api:exchange_confirm", args=[ex_id]))
        self.assertEqual(resp.json()["result"], "completed")

    def test_business_rule_error_returns_400(self):
        # Requesting a non-match surfaces a clean 400, not a 500.
        rio = self._user("rio@x.com")  # no skills -> not a match
        self.client.force_login(self.alex)
        resp = self.client.post(
            reverse("api:request_create"),
            {"receiver_id": rio.pk, "offered_skill_id": self.python.pk,
             "requested_skill_id": self.uiux.pk},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("detail", resp.json())

    def test_non_participant_cannot_view_exchange(self):
        req = exchange_services.create_request(self.alex, self.sam, self.python, self.uiux)
        ex = exchange_services.accept_request(req, self.sam)
        rio = self._user("rio@x.com")
        self.client.force_login(rio)
        resp = self.client.get(reverse("api:exchange_detail", args=[ex.pk]))
        self.assertEqual(resp.status_code, 404)  # no existence leak


class ApiMessagingTests(ApiBase):
    def _exchange(self):
        req = exchange_services.create_request(self.alex, self.sam, self.python, self.uiux)
        return exchange_services.accept_request(req, self.sam)

    def test_participant_can_send_and_list_messages(self):
        ex = self._exchange()
        self.client.force_login(self.alex)
        resp = self.client.post(
            reverse("api:message_send", args=[ex.pk]),
            {"body": "Hello Sam"},
        )
        self.assertEqual(resp.status_code, 201)
        resp = self.client.get(reverse("api:messages", args=[ex.pk]))
        bodies = [m["body"] for m in resp.json()["messages"]]
        self.assertIn("Hello Sam", bodies)

    def test_non_participant_cannot_send(self):
        ex = self._exchange()
        rio = self._user("rio@x.com")
        self.client.force_login(rio)
        resp = self.client.post(
            reverse("api:message_send", args=[ex.pk]), {"body": "intrude"}
        )
        self.assertEqual(resp.status_code, 404)

    def test_empty_message_rejected(self):
        ex = self._exchange()
        self.client.force_login(self.alex)
        resp = self.client.post(reverse("api:message_send", args=[ex.pk]), {"body": "  "})
        self.assertEqual(resp.status_code, 400)


class ApiCsrfTests(ApiBase):
    def test_session_auth_write_requires_csrf_token(self):
        # DRF SessionAuthentication enforces CSRF on unsafe methods. A session-
        # authenticated POST without a CSRF token must be rejected (403).
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.alex)
        resp = csrf_client.post(
            reverse("api:my_skills"),
            {"skill_id": self.uiux.pk, "kind": SkillKind.WANT},
        )
        self.assertEqual(resp.status_code, 403)


class ApiSuspensionTests(ApiBase):
    def test_suspended_user_blocked_from_api(self):
        self.client.force_login(self.alex)
        self.alex.is_suspended = True
        self.alex.save()
        # Middleware returns a JSON 403 for /api/ paths.
        resp = self.client.get(reverse("api:me"))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("code"), "account_suspended")
