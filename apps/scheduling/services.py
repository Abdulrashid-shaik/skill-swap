"""Learning-session lifecycle (M8). Participants only; every change notifies
the other participant. Google Calendar sync (P9) hooks in here later."""
from django.utils import timezone

from apps.common.exceptions import BusinessRuleError
from apps.notifications.models import NotificationType
from apps.notifications.services import notify

from .models import ExchangeSession, SessionStatus


def _require_participant(exchange, user):
    if not exchange.includes(user):
        raise BusinessRuleError("You are not a participant in this exchange.")


def create_session(exchange, user, *, title, description, start, end):
    _require_participant(exchange, user)
    session = ExchangeSession.objects.create(
        exchange=exchange, created_by=user, title=title, description=description,
        scheduled_start=start, scheduled_end=end,
    )
    notify(
        exchange.other_participant(user), NotificationType.SESSION_SCHEDULED,
        f"New session scheduled: {title}",
        target_url=f"/exchanges/{exchange.pk}/sessions/",
    )
    # Google Calendar sync — no-op unless the integration is enabled (P9).
    from apps.integrations.services import sync_new_session
    sync_new_session(session)
    return session


def reschedule_session(session, user, *, start, end):
    exchange = session.exchange
    _require_participant(exchange, user)
    if session.status not in (SessionStatus.SCHEDULED,):
        raise BusinessRuleError("Only a scheduled session can be rescheduled.")
    session.status = SessionStatus.RESCHEDULED
    session.save(update_fields=["status", "updated_at"])
    new_session = ExchangeSession.objects.create(
        exchange=exchange, created_by=user, title=session.title,
        description=session.description, scheduled_start=start, scheduled_end=end,
        previous_session=session,
    )
    notify(
        exchange.other_participant(user), NotificationType.SESSION_RESCHEDULED,
        f"Session rescheduled: {session.title}",
        target_url=f"/exchanges/{exchange.pk}/sessions/",
    )
    return new_session


def cancel_session(session, user):
    exchange = session.exchange
    _require_participant(exchange, user)
    if session.status not in (SessionStatus.SCHEDULED,):
        raise BusinessRuleError("Only a scheduled session can be cancelled.")
    session.status = SessionStatus.CANCELLED
    session.save(update_fields=["status", "updated_at"])
    notify(
        exchange.other_participant(user), NotificationType.SESSION_CANCELLED,
        f"Session cancelled: {session.title}",
        target_url=f"/exchanges/{exchange.pk}/sessions/",
    )
    from apps.integrations.services import sync_cancelled_session
    sync_cancelled_session(session)


def complete_session(session, user):
    _require_participant(session.exchange, user)
    if session.status != SessionStatus.SCHEDULED:
        raise BusinessRuleError("Only a scheduled session can be completed.")
    session.status = SessionStatus.COMPLETED
    session.save(update_fields=["status", "updated_at"])
