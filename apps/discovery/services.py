"""Mutual-matching engine (M4).

Strict rule: users A and B are a valid match ONLY when each offers at least
one skill the other wants — in BOTH directions. Matching is computed on demand
with ORM queries; nothing is stored. The helpers here are also the server-side
re-validation used when creating and accepting exchange requests (P5).
"""
from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.moderation.services import blocked_pair_ids
from apps.skills.models import Skill, SkillKind, SkillStatus, UserSkill


def _not_currently_suspended_q():
    """Q matching users who are NOT under an active suspension: either not
    suspended, or suspended with a ``suspended_until`` that has already passed
    (expired). Mirrors User.is_currently_suspended at the queryset level so
    discovery honors auto-expiry (R12) instead of hiding reinstated members."""
    return Q(is_suspended=False) | Q(suspended_until__lte=timezone.now())


def _skill_ids(user, kind):
    """Approved, active skill IDs the user has in the given list (OFFER/WANT)."""
    return set(
        UserSkill.objects.filter(
            user=user,
            kind=kind,
            is_active=True,
            skill__status=SkillStatus.APPROVED,
            skill__is_active=True,
        ).values_list("skill_id", flat=True)
    )


def discoverable_users_qs(user):
    """Users who may appear to `user`: active, not deactivated, not suspended,
    not self, not blocked (either direction)."""
    return (
        User.objects.filter(
            _not_currently_suspended_q(), is_active=True, is_deactivated=False
        )
        .exclude(pk=user.pk)
        .exclude(pk__in=blocked_pair_ids(user))
    )


def are_mutually_compatible(a, b):
    """Strict mutual-match check. Used by discovery AND by exchange request
    create/accept for server-side re-validation (never trust the client)."""
    if a.pk == b.pk:
        return False
    if not discoverable_users_qs(a).filter(pk=b.pk).exists():
        return False
    a_offers, a_wants = _skill_ids(a, SkillKind.OFFER), _skill_ids(a, SkillKind.WANT)
    b_offers, b_wants = _skill_ids(b, SkillKind.OFFER), _skill_ids(b, SkillKind.WANT)
    return bool(a_offers & b_wants) and bool(b_offers & a_wants)


def exchangeable_skills(a, b):
    """Return (skills a can teach b, skills b can teach a) as Skill lists.
    Bidirectional set intersection; drives both the UI and exchange creation."""
    a_offers, a_wants = _skill_ids(a, SkillKind.OFFER), _skill_ids(a, SkillKind.WANT)
    b_offers, b_wants = _skill_ids(b, SkillKind.OFFER), _skill_ids(b, SkillKind.WANT)
    a_teaches_b = a_offers & b_wants
    b_teaches_a = b_offers & a_wants
    return (
        list(Skill.objects.filter(pk__in=a_teaches_b)),
        list(Skill.objects.filter(pk__in=b_teaches_a)),
    )


def get_matches(user, *, q=None, category=None, proficiency=None):
    """Return the list of valid matches for `user`, each as a dict:
        {user, they_teach_me (UserSkill list), i_teach_them (Skill list), score}

    Optional filters narrow the "they can teach me" side:
      - q: skill-name contains
      - category: category slug
      - proficiency: exact proficiency on what they'd teach me
    """
    my_offers = _skill_ids(user, SkillKind.OFFER)
    my_wants = _skill_ids(user, SkillKind.WANT)
    if not my_offers or not my_wants:
        return []  # mutual match impossible without both an offer and a want

    candidates = discoverable_users_qs(user)

    want_my_offer_ids = set(
        UserSkill.objects.filter(
            kind=SkillKind.WANT, is_active=True,
            skill_id__in=my_offers, user__in=candidates,
            skill__status=SkillStatus.APPROVED, skill__is_active=True,
        ).values_list("user_id", flat=True)
    )
    offer_my_want_ids = set(
        UserSkill.objects.filter(
            kind=SkillKind.OFFER, is_active=True,
            skill_id__in=my_wants, user__in=candidates,
            skill__status=SkillStatus.APPROVED, skill__is_active=True,
        ).values_list("user_id", flat=True)
    )
    match_ids = want_my_offer_ids & offer_my_want_ids  # strict both-directions
    if not match_ids:
        return []

    # What each match can teach me = their OFFERs that are in my wants.
    teach_me = (
        UserSkill.objects.filter(
            kind=SkillKind.OFFER, is_active=True,
            skill_id__in=my_wants, user_id__in=match_ids,
            skill__status=SkillStatus.APPROVED, skill__is_active=True,
        )
        .select_related("skill", "skill__category")
    )
    # What I can teach each match = my offers that are in their wants.
    teach_them = (
        UserSkill.objects.filter(
            kind=SkillKind.WANT, is_active=True,
            skill_id__in=my_offers, user_id__in=match_ids,
        )
        .select_related("skill")
    )

    by_teach_me = defaultdict(list)
    for us in teach_me:
        by_teach_me[us.user_id].append(us)
    by_teach_them = defaultdict(list)
    for us in teach_them:
        by_teach_them[us.user_id].append(us.skill)

    filtering = bool(q or category or proficiency)

    def apply_filters(items):
        if category:
            items = [u for u in items if u.skill.category.slug == category]
        if proficiency:
            items = [u for u in items if u.proficiency == proficiency]
        if q:
            ql = q.lower()
            items = [u for u in items if ql in u.skill.name.lower()]
        return items

    users_by_id = {
        u.pk: u
        for u in candidates.filter(pk__in=match_ids).select_related("profile")
    }

    results = []
    for uid in match_ids:
        teach_me_items = by_teach_me.get(uid, [])
        if filtering:
            teach_me_items = apply_filters(teach_me_items)
            if not teach_me_items:
                continue
        i_teach = by_teach_them.get(uid, [])
        results.append(
            {
                "user": users_by_id[uid],
                "they_teach_me": teach_me_items,   # UserSkill (carries proficiency)
                "i_teach_them": i_teach,           # Skill list
                "score": len(teach_me_items) + len(i_teach),
            }
        )

    results.sort(key=lambda r: (-r["score"], r["user"].pk))
    return results
