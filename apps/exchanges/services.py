"""Exchange request + lifecycle business logic (M5/M6).

All rules are enforced here, server-side, inside transactions. Views call these
functions; they never mutate status directly.
"""
from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import BusinessRuleError
from apps.discovery.services import are_mutually_compatible, exchangeable_skills
from apps.moderation.services import is_blocked_between
from apps.notifications.models import NotificationType
from apps.notifications.services import notify

from .models import (Exchange, ExchangeConfirmation, ExchangeRequest,
                     ExchangeStatus, RequestStatus)


def create_request(sender, receiver, offered_skill, requested_skill, message=""):
    if sender.pk == receiver.pk:
        raise BusinessRuleError("You cannot send a request to yourself.")
    if is_blocked_between(sender, receiver):
        raise BusinessRuleError("This member is unavailable.")
    if not are_mutually_compatible(sender, receiver):
        raise BusinessRuleError("You are not a mutual match with this member.")

    # The chosen skills must be part of the valid two-way exchange.
    a_teaches, b_teaches = exchangeable_skills(sender, receiver)
    if offered_skill not in a_teaches or requested_skill not in b_teaches:
        raise BusinessRuleError("The selected skills are not a valid exchange.")

    if ExchangeRequest.objects.filter(
        sender=sender, receiver=receiver, status=RequestStatus.PENDING
    ).exists():
        raise BusinessRuleError("You already have a pending request to this member.")

    with transaction.atomic():
        req = ExchangeRequest.objects.create(
            sender=sender, receiver=receiver,
            offered_skill=offered_skill, requested_skill=requested_skill,
            message=message,
        )
        notify(
            receiver, NotificationType.REQUEST_RECEIVED,
            f"{sender.profile.full_name or sender.email} sent you an exchange request",
            target_url="/requests/received/",
        )
    return req


def accept_request(req, user):
    if req.receiver_id != user.pk:
        raise BusinessRuleError("Only the receiver can accept this request.")
    if req.status != RequestStatus.PENDING:
        raise BusinessRuleError("This request is no longer pending.")
    # Re-validate mutual compatibility at accept time (never trust stale state).
    if not are_mutually_compatible(req.sender, req.receiver):
        raise BusinessRuleError("You are no longer a mutual match.")

    with transaction.atomic():
        req.status = RequestStatus.ACCEPTED
        req.responded_at = timezone.now()
        req.save(update_fields=["status", "responded_at", "updated_at"])
        exchange = Exchange.objects.create(
            request=req,
            participant_a=req.sender, participant_b=req.receiver,
            skill_a_teaches=req.offered_skill, skill_b_teaches=req.requested_skill,
        )
        notify(
            req.sender, NotificationType.REQUEST_ACCEPTED,
            f"{req.receiver.profile.full_name or req.receiver.email} accepted your request",
            target_url=f"/exchanges/{exchange.pk}/",
        )
    return exchange


def reject_request(req, user):
    if req.receiver_id != user.pk:
        raise BusinessRuleError("Only the receiver can reject this request.")
    if req.status != RequestStatus.PENDING:
        raise BusinessRuleError("This request is no longer pending.")
    with transaction.atomic():
        req.status = RequestStatus.REJECTED
        req.responded_at = timezone.now()
        req.save(update_fields=["status", "responded_at", "updated_at"])
        notify(
            req.sender, NotificationType.REQUEST_REJECTED,
            "Your exchange request was declined",
            target_url="/requests/sent/",
        )


def cancel_request(req, user):
    if req.sender_id != user.pk:
        raise BusinessRuleError("Only the sender can cancel this request.")
    if req.status != RequestStatus.PENDING:
        raise BusinessRuleError("This request is no longer pending.")
    with transaction.atomic():
        req.status = RequestStatus.CANCELLED
        req.responded_at = timezone.now()
        req.save(update_fields=["status", "responded_at", "updated_at"])
        notify(
            req.receiver, NotificationType.REQUEST_CANCELLED,
            "An exchange request was cancelled",
            target_url="/requests/received/",
        )


def confirm_exchange(exchange_id, user):
    """Dual completion confirmation. The first confirmation leaves the exchange
    ONGOING; only when BOTH participants have confirmed does it become
    COMPLETED. Race-safe via the atomic block + the unique(exchange, user)
    constraint + an in-transaction re-read."""
    with transaction.atomic():
        exchange = Exchange.objects.select_for_update().get(pk=exchange_id)
        if not exchange.includes(user):
            raise BusinessRuleError("You are not a participant in this exchange.")
        if exchange.status != ExchangeStatus.ONGOING:
            raise BusinessRuleError("This exchange is not ongoing.")

        ExchangeConfirmation.objects.get_or_create(exchange=exchange, user=user)

        if exchange.confirmations.count() >= 2:
            exchange.status = ExchangeStatus.COMPLETED
            exchange.completed_at = timezone.now()
            exchange.save(update_fields=["status", "completed_at", "updated_at"])
            # Bump the completed-exchange counters.
            for p in (exchange.participant_a, exchange.participant_b):
                p.profile.completed_exchanges = p.profile.completed_exchanges + 1
                p.profile.save(update_fields=["completed_exchanges", "updated_at"])
                notify(
                    p, NotificationType.EXCHANGE_COMPLETED,
                    "Exchange completed",
                    target_url=f"/exchanges/{exchange.pk}/",
                )
            return "completed"
        else:
            notify(
                exchange.other_participant(user),
                NotificationType.CONFIRMATION_RECORDED,
                "Your partner confirmed completion — confirm when you're done too",
                target_url=f"/exchanges/{exchange.pk}/",
            )
            return "awaiting_other"


def cancel_exchange(exchange_id, user):
    with transaction.atomic():
        exchange = Exchange.objects.select_for_update().get(pk=exchange_id)
        if not exchange.includes(user):
            raise BusinessRuleError("You are not a participant in this exchange.")
        if exchange.status != ExchangeStatus.ONGOING:
            raise BusinessRuleError("This exchange is not ongoing.")
        exchange.status = ExchangeStatus.CANCELLED
        exchange.cancelled_at = timezone.now()
        exchange.cancelled_by = user
        exchange.save(update_fields=["status", "cancelled_at", "cancelled_by", "updated_at"])
        notify(
            exchange.other_participant(user),
            NotificationType.EXCHANGE_CANCELLED,
            "An exchange was cancelled",
            target_url=f"/exchanges/{exchange.pk}/",
        )
