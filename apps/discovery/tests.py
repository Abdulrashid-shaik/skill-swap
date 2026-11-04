from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.moderation.models import UserBlock
from apps.skills.models import (Proficiency, Skill, SkillCategory, SkillKind,
                                SkillStatus, UserSkill)

from .services import (are_mutually_compatible, exchangeable_skills, get_matches)


class MatchingTestBase(TestCase):
    def setUp(self):
        self.cat = SkillCategory.objects.create(name="Programming")
        self.design = SkillCategory.objects.create(name="Design")
        self.python = Skill.objects.create(
            name="Python", category=self.cat, status=SkillStatus.APPROVED)
        self.uiux = Skill.objects.create(
            name="UI/UX", category=self.design, status=SkillStatus.APPROVED)
        self.sql = Skill.objects.create(
            name="SQL", category=self.cat, status=SkillStatus.APPROVED)

    def make_user(self, email, offers=(), wants=()):
        user = User.objects.create_user(email=email, password="pw-strong-123")
        for skill, prof in offers:
            UserSkill.objects.create(user=user, skill=skill, kind=SkillKind.OFFER,
                                     proficiency=prof)
        for skill in wants:
            UserSkill.objects.create(user=user, skill=skill, kind=SkillKind.WANT)
        return user


class MutualMatchTests(MatchingTestBase):
    def test_valid_mutual_match_both_directions(self):
        a = self.make_user("a@x.com", offers=[(self.python, Proficiency.ADVANCED)], wants=[self.uiux])
        b = self.make_user("b@x.com", offers=[(self.uiux, Proficiency.EXPERT)], wants=[self.python])
        self.assertTrue(are_mutually_compatible(a, b))
        self.assertTrue(are_mutually_compatible(b, a))
        matches = get_matches(a)
        self.assertEqual([m["user"].pk for m in matches], [b.pk])
        self.assertEqual([s.name for s in matches[0]["i_teach_them"]], ["Python"])
        self.assertEqual([u.skill.name for u in matches[0]["they_teach_me"]], ["UI/UX"])

    def test_one_way_is_not_a_match(self):
        # B wants what A offers, but B does NOT offer what A wants.
        a = self.make_user("a@x.com", offers=[(self.python, "")], wants=[self.uiux])
        b = self.make_user("b@x.com", offers=[(self.sql, "")], wants=[self.python])
        self.assertFalse(are_mutually_compatible(a, b))
        self.assertEqual(get_matches(a), [])

    def test_no_match_when_user_has_no_wants(self):
        a = self.make_user("a@x.com", offers=[(self.python, "")])
        self.make_user("b@x.com", offers=[(self.uiux, "")], wants=[self.python])
        self.assertEqual(get_matches(a), [])

    def test_exchangeable_skills(self):
        a = self.make_user("a@x.com", offers=[(self.python, "")], wants=[self.uiux])
        b = self.make_user("b@x.com", offers=[(self.uiux, "")], wants=[self.python])
        a_teaches_b, b_teaches_a = exchangeable_skills(a, b)
        self.assertEqual([s.name for s in a_teaches_b], ["Python"])
        self.assertEqual([s.name for s in b_teaches_a], ["UI/UX"])


class ExclusionTests(MatchingTestBase):
    def setUp(self):
        super().setUp()
        self.a = self.make_user("a@x.com", offers=[(self.python, "")], wants=[self.uiux])
        self.b = self.make_user("b@x.com", offers=[(self.uiux, "")], wants=[self.python])

    def test_self_excluded(self):
        self.assertNotIn(self.a.pk, [m["user"].pk for m in get_matches(self.a)])

    def test_blocked_excluded_both_directions(self):
        UserBlock.objects.create(blocker=self.a, blocked=self.b)
        self.assertEqual(get_matches(self.a), [])
        self.assertEqual(get_matches(self.b), [])  # reverse direction too
        self.assertFalse(are_mutually_compatible(self.a, self.b))

    def test_deactivated_excluded(self):
        self.b.is_deactivated = True
        self.b.is_active = False
        self.b.save()
        self.assertEqual(get_matches(self.a), [])

    def test_suspended_excluded(self):
        self.b.is_suspended = True
        self.b.save()
        self.assertEqual(get_matches(self.a), [])


class FilterTests(MatchingTestBase):
    def test_category_and_proficiency_filters(self):
        a = self.make_user("a@x.com", offers=[(self.python, "")], wants=[self.uiux, self.sql])
        # b teaches UI/UX (Design, expert); a wants UI/UX and SQL, offers Python which b wants
        b = self.make_user("b@x.com", offers=[(self.uiux, Proficiency.EXPERT)], wants=[self.python])
        # category filter: Programming → b teaches only Design → filtered out
        self.assertEqual(get_matches(a, category="programming"), [])
        # category filter: design → b stays
        self.assertEqual([m["user"].pk for m in get_matches(a, category="design")], [b.pk])
        # proficiency filter: beginner → b is expert → filtered out
        self.assertEqual(get_matches(a, proficiency=Proficiency.BEGINNER), [])
        # proficiency filter: expert → b stays
        self.assertEqual([m["user"].pk for m in get_matches(a, proficiency=Proficiency.EXPERT)], [b.pk])
        # skill-name search
        self.assertEqual([m["user"].pk for m in get_matches(a, q="ui")], [b.pk])
        self.assertEqual(get_matches(a, q="python"), [])  # they don't teach Python


class DiscoverViewTests(MatchingTestBase):
    def test_discover_requires_authentication(self):
        resp = self.client.get(reverse("discover"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_discover_lists_match(self):
        a = self.make_user("a@x.com", offers=[(self.python, "")], wants=[self.uiux])
        self.make_user("b@x.com", offers=[(self.uiux, "")], wants=[self.python])
        self.client.force_login(a)
        resp = self.client.get(reverse("discover"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "b@x.com")
        self.assertContains(resp, "UI/UX")
