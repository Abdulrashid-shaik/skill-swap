"""Messaging logic shared by the template views and the DRF API (no dup)."""
from django.utils import timezone

from apps.common.exceptions import BusinessRuleError
from apps.common.suspension import ensure_not_suspended
from apps.notifications.models import NotificationType
from apps.notifications.services import notify

from .models import Message


def serialize_message(message, me):
    return {
        "id": message.pk,
        "sender": message.sender.profile.full_name or message.sender.email,
        "body": message.body,
        "is_me": message.sender_id == me.pk,
        "created": timezone.localtime(message.created_at).strftime("%b %d, %H:%M"),
    }


def mark_incoming_read(exchange, user):
    """Mark the OTHER participant's unread messages as read (never your own)."""
    exchange.messages.exclude(sender=user).filter(is_read=False).update(
        is_read=True, read_at=timezone.now()
    )


def post_message(exchange, sender, body):
    """Create a message from ``sender`` in ``exchange`` and notify the partner.
    Raises BusinessRuleError if the sender is suspended or the body is empty."""
    ensure_not_suspended(sender)
    body = (body or "").strip()
    if not body:
        raise BusinessRuleError("Message cannot be empty.")
    message = Message.objects.create(exchange=exchange, sender=sender, body=body)
    notify(
        exchange.other_participant(sender),
        NotificationType.MESSAGE_RECEIVED,
        "New message in your exchange",
        target_url=f"/exchanges/{exchange.pk}/chat/",
    )
    return message
