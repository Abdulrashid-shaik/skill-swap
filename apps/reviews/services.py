from decimal import Decimal

from django.db import transaction
from django.db.models import Avg

from apps.common.exceptions import BusinessRuleError
from apps.exchanges.models import ExchangeStatus
from apps.notifications.models import NotificationType
from apps.notifications.services import notify

from .models import Review


def create_review(exchange, reviewer, rating, feedback=""):
    if exchange.status != ExchangeStatus.COMPLETED:
        raise BusinessRuleError("You can only review a completed exchange.")
    if not exchange.includes(reviewer):
        raise BusinessRuleError("Only a participant can review this exchange.")
    if Review.objects.filter(exchange=exchange, reviewer=reviewer).exists():
        raise BusinessRuleError("You have already reviewed this exchange.")

    reviewee = exchange.other_participant(reviewer)
    with transaction.atomic():
        review = Review.objects.create(
            exchange=exchange, reviewer=reviewer, reviewee=reviewee,
            rating=rating, feedback=feedback,
        )
        _refresh_rating(reviewee)
        notify(
            reviewee, NotificationType.REVIEW_RECEIVED,
            "You received a new review",
            target_url=f"/members/{reviewer.pk}/",
        )
    return review


def _refresh_rating(user):
    agg = Review.objects.filter(reviewee=user).aggregate(
        avg=Avg("rating"), )
    qs = Review.objects.filter(reviewee=user)
    profile = user.profile
    profile.rating_count = qs.count()
    profile.rating_avg = Decimal(str(round(agg["avg"] or 0, 2)))
    profile.save(update_fields=["rating_avg", "rating_count", "updated_at"])
