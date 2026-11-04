from apps.common.exceptions import BusinessRuleError

from .models import UserBlock, UserReport


def block_user(blocker, blocked):
    if blocker.pk == blocked.pk:
        raise BusinessRuleError("You cannot block yourself.")
    UserBlock.objects.get_or_create(blocker=blocker, blocked=blocked)


def unblock_user(blocker, blocked):
    UserBlock.objects.filter(blocker=blocker, blocked=blocked).delete()


def is_blocking(blocker, blocked):
    return UserBlock.objects.filter(blocker=blocker, blocked=blocked).exists()


def report_user(reporter, reported, reason, description=""):
    if reporter.pk == reported.pk:
        raise BusinessRuleError("You cannot report yourself.")
    return UserReport.objects.create(
        reporter=reporter, reported=reported, reason=reason, description=description)


def blocked_pair_ids(user):
    """IDs of users who are blocked by `user` OR who have blocked `user`.

    Used to exclude them from discovery/matching and to forbid new requests
    in either direction.
    """
    made = UserBlock.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    received = UserBlock.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    return set(made) | set(received)


def is_blocked_between(a, b):
    """True if either user has blocked the other."""
    return UserBlock.objects.filter(
        blocker__in=[a, b], blocked__in=[a, b]
    ).exists()
